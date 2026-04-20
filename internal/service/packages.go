package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"tpops_deployment/internal/repository"
)

type PackageReleaseOut struct {
	ID                int64  `json:"id"`
	Name              string `json:"name"`
	Description       string `json:"description"`
	CreatedAt         string `json:"created_at"`
	ArtifactCount     int    `json:"artifact_count"`
	CreatedByUsername string `json:"created_by_username,omitempty"`
}

type PackageArtifactOut struct {
	ID             int64  `json:"id"`
	Release        int64  `json:"release"`
	OriginalName   string `json:"original_name"`
	RemoteBasename string `json:"remote_basename"`
	Size           int64  `json:"size"`
	Sha256         string `json:"sha256"`
	CreatedAt      string `json:"created_at"`
}

type CreateReleaseIn struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

func (s *Service) ListPackageReleases(ctx context.Context) ([]PackageReleaseOut, error) {
	rows, err := s.repos.ListPackageReleases(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]PackageReleaseOut, 0, len(rows))
	for _, r := range rows {
		o := PackageReleaseOut{
			ID:            r.ID,
			Name:          r.Name,
			Description:   r.Description,
			CreatedAt:     r.CreatedAt,
			ArtifactCount: r.ArtifactCount,
		}
		if r.OwnerUsername.Valid {
			o.CreatedByUsername = r.OwnerUsername.String
		}
		out = append(out, o)
	}
	return out, nil
}

func (s *Service) CreatePackageRelease(ctx context.Context, userID int64, in CreateReleaseIn) (*PackageReleaseOut, int, error) {
	name := strings.TrimSpace(in.Name)
	if name == "" {
		return nil, http.StatusBadRequest, errors.New("请填写版本名称")
	}
	uid := userID
	id, err := s.repos.InsertPackageRelease(ctx, name, strings.TrimSpace(in.Description), &uid)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	r, err := s.repos.GetPackageReleaseByID(ctx, id)
	if err != nil || r == nil {
		return nil, http.StatusInternalServerError, errors.New("创建后读取失败")
	}
	return releaseToOut(r), http.StatusCreated, nil
}

func releaseToOut(r *repository.PackageRelease) *PackageReleaseOut {
	if r == nil {
		return nil
	}
	o := &PackageReleaseOut{
		ID:            r.ID,
		Name:          r.Name,
		Description:   r.Description,
		CreatedAt:     r.CreatedAt,
		ArtifactCount: r.ArtifactCount,
	}
	if r.OwnerUsername.Valid {
		o.CreatedByUsername = r.OwnerUsername.String
	}
	return o
}

func (s *Service) DeletePackageRelease(ctx context.Context, userID, id int64) (int, error) {
	r, err := s.repos.GetPackageReleaseByID(ctx, id)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if r == nil {
		return http.StatusNotFound, errors.New("未找到")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, r.CreatedByID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if !ok {
		return http.StatusForbidden, errors.New("无权删除")
	}
	arts, _ := s.repos.ListArtifactsByRelease(ctx, id)
	for _, a := range arts {
		if a.StoragePath != "" {
			_ = os.Remove(a.StoragePath)
		}
	}
	n, err := s.repos.DeletePackageRelease(ctx, id)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if n == 0 {
		return http.StatusNotFound, errors.New("未找到")
	}
	return http.StatusNoContent, nil
}

func (s *Service) ListArtifacts(ctx context.Context, userID, releaseID int64) ([]PackageArtifactOut, int, error) {
	r, err := s.repos.GetPackageReleaseByID(ctx, releaseID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if r == nil {
		return nil, http.StatusNotFound, errors.New("未找到版本")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, r.CreatedByID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if !ok {
		return nil, http.StatusForbidden, errors.New("无权查看")
	}
	rows, err := s.repos.ListArtifactsByRelease(ctx, releaseID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	out := make([]PackageArtifactOut, 0, len(rows))
	for _, a := range rows {
		out = append(out, artifactToOut(&a))
	}
	return out, http.StatusOK, nil
}

func artifactToOut(a *repository.PackageArtifact) PackageArtifactOut {
	return PackageArtifactOut{
		ID:             a.ID,
		Release:        a.ReleaseID,
		OriginalName:   a.OriginalName,
		RemoteBasename: a.RemoteBasename,
		Size:           a.Size,
		Sha256:         a.Sha256,
		CreatedAt:      a.CreatedAt,
	}
}

func (s *Service) UploadArtifact(ctx context.Context, userID, releaseID int64, fileHeader *multipart.FileHeader, file multipart.File) (*PackageArtifactOut, int, error) {
	if fileHeader == nil || file == nil {
		return nil, http.StatusBadRequest, errors.New("缺少上传文件")
	}
	r, err := s.repos.GetPackageReleaseByID(ctx, releaseID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if r == nil {
		return nil, http.StatusNotFound, errors.New("未找到版本")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, r.CreatedByID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if !ok {
		return nil, http.StatusForbidden, errors.New("无权上传")
	}
	orig := filepath.Base(strings.TrimSpace(fileHeader.Filename))
	if orig == "" || orig == "." {
		orig = "upload.bin"
	}
	basename := orig
	sum := sha256.New()
	dir := filepath.Join(s.cfg.PackagesStorageDir, fmt.Sprintf("release_%d", releaseID))
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return nil, http.StatusInternalServerError, err
	}
	dest := filepath.Join(dir, basename)
	existing, err := s.repos.FindArtifactByReleaseAndBasename(ctx, releaseID, basename)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if existing != nil && existing.StoragePath != "" {
		dest = existing.StoragePath
	}
	outf, err := os.Create(dest)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	defer outf.Close()
	mw := io.MultiWriter(outf, sum)
	written, err := io.Copy(mw, file)
	if err != nil {
		_ = os.Remove(dest)
		return nil, http.StatusInternalServerError, err
	}
	hash := hex.EncodeToString(sum.Sum(nil))
	n := written
	uid := userID

	if existing != nil {
		if err := s.repos.UpdateArtifactFile(ctx, existing.ID, orig, dest, n, hash); err != nil {
			return nil, http.StatusInternalServerError, err
		}
		a, err := s.repos.GetArtifact(ctx, existing.ID)
		if err != nil || a == nil {
			return nil, http.StatusInternalServerError, errors.New("更新后读取失败")
		}
		o := artifactToOut(a)
		return &o, http.StatusOK, nil
	}

	id, err := s.repos.InsertArtifact(ctx, releaseID, orig, basename, dest, n, hash, &uid)
	if err != nil {
		_ = os.Remove(dest)
		return nil, http.StatusInternalServerError, err
	}
	a, err := s.repos.GetArtifact(ctx, id)
	if err != nil || a == nil {
		return nil, http.StatusInternalServerError, errors.New("插入后读取失败")
	}
	o := artifactToOut(a)
	return &o, http.StatusCreated, nil
}

func (s *Service) DeleteArtifact(ctx context.Context, userID, artifactID int64) (int, error) {
	a, err := s.repos.GetArtifact(ctx, artifactID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if a == nil {
		return http.StatusNotFound, errors.New("未找到")
	}
	cb, err := s.repos.ReleaseCreatedBy(ctx, a.ReleaseID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, cb)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if !ok {
		return http.StatusForbidden, errors.New("无权删除")
	}
	if a.StoragePath != "" {
		_ = os.Remove(a.StoragePath)
	}
	n, err := s.repos.DeleteArtifact(ctx, artifactID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if n == 0 {
		return http.StatusNotFound, errors.New("未找到")
	}
	return http.StatusNoContent, nil
}
