package repository

import (
	"context"
	"database/sql"
	"strings"
)

type PackageRelease struct {
	ID            int64          `db:"id"`
	Name          string         `db:"name"`
	Description   string         `db:"description"`
	CreatedByID   *int64         `db:"created_by_id"`
	CreatedAt     string         `db:"created_at"`
	UpdatedAt     string         `db:"updated_at"`
	ArtifactCount int            `db:"artifact_count"`
	OwnerUsername sql.NullString `db:"owner_username"`
}

func (r *Repos) InsertPackageRelease(ctx context.Context, name, description string, createdBy *int64) (int64, error) {
	res, err := r.db.ExecContext(ctx, `
		INSERT INTO packages_packagerelease (name, description, created_by_id, created_at, updated_at)
		VALUES (?, ?, ?, datetime('now'), datetime('now'))`,
		name, description, createdBy)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (r *Repos) GetPackageReleaseByID(ctx context.Context, id int64) (*PackageRelease, error) {
	var row PackageRelease
	err := r.db.GetContext(ctx, &row, `
		SELECT r.id, r.name, r.description, r.created_by_id, r.created_at, r.updated_at,
		       (SELECT COUNT(*) FROM packages_packageartifact a WHERE a.release_id = r.id) AS artifact_count,
		       u.username AS owner_username
		FROM packages_packagerelease r
		LEFT JOIN auth_user u ON u.id = r.created_by_id
		WHERE r.id = ?`, id)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &row, nil
}

func (r *Repos) ListPackageReleases(ctx context.Context) ([]PackageRelease, error) {
	var rows []PackageRelease
	err := r.db.SelectContext(ctx, &rows, `
		SELECT r.id, r.name, r.description, r.created_by_id, r.created_at, r.updated_at,
		       (SELECT COUNT(*) FROM packages_packageartifact a WHERE a.release_id = r.id) AS artifact_count,
		       u.username AS owner_username
		FROM packages_packagerelease r
		LEFT JOIN auth_user u ON u.id = r.created_by_id
		ORDER BY r.created_at DESC`)
	return rows, err
}

func (r *Repos) DeletePackageRelease(ctx context.Context, id int64) (int64, error) {
	res, err := r.db.ExecContext(ctx, `DELETE FROM packages_packagerelease WHERE id = ?`, id)
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}

type PackageArtifact struct {
	ID             int64  `db:"id"`
	ReleaseID      int64  `db:"release_id"`
	OriginalName   string `db:"original_name"`
	RemoteBasename string `db:"remote_basename"`
	StoragePath    string `db:"storage_path"`
	Size           int64  `db:"size"`
	Sha256         string `db:"sha256"`
	CreatedAt      string `db:"created_at"`
}

// ListArtifactsByIDs 按主键批量读取（用于任务关联的安装包）。
func (r *Repos) ListArtifactsByIDs(ctx context.Context, ids []int64) ([]PackageArtifact, error) {
	if len(ids) == 0 {
		return nil, nil
	}
	placeholders := make([]string, len(ids))
	args := make([]interface{}, len(ids))
	for i, id := range ids {
		placeholders[i] = "?"
		args[i] = id
	}
	q := "SELECT id, release_id, original_name, remote_basename, storage_path, size, sha256, created_at FROM packages_packageartifact WHERE id IN (" +
		strings.Join(placeholders, ",") + ") ORDER BY id"
	var rows []PackageArtifact
	err := r.db.SelectContext(ctx, &rows, q, args...)
	return rows, err
}

func (r *Repos) ListArtifactsByRelease(ctx context.Context, releaseID int64) ([]PackageArtifact, error) {
	var rows []PackageArtifact
	err := r.db.SelectContext(ctx, &rows, `
		SELECT id, release_id, original_name, remote_basename, storage_path, size, sha256, created_at
		FROM packages_packageartifact WHERE release_id = ? ORDER BY id DESC`, releaseID)
	return rows, err
}

func (r *Repos) InsertArtifact(ctx context.Context, releaseID int64, originalName, remoteBasename, storagePath string, size int64, sha256 string, createdBy *int64) (int64, error) {
	res, err := r.db.ExecContext(ctx, `
		INSERT INTO packages_packageartifact (release_id, original_name, remote_basename, storage_path, size, sha256, created_by_id, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))`,
		releaseID, originalName, remoteBasename, storagePath, size, sha256, createdBy)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (r *Repos) GetArtifact(ctx context.Context, id int64) (*PackageArtifact, error) {
	var a PackageArtifact
	err := r.db.GetContext(ctx, &a, `
		SELECT id, release_id, original_name, remote_basename, storage_path, size, sha256, created_at
		FROM packages_packageartifact WHERE id = ?`, id)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &a, nil
}

func (r *Repos) FindArtifactByReleaseAndBasename(ctx context.Context, releaseID int64, basename string) (*PackageArtifact, error) {
	var a PackageArtifact
	err := r.db.GetContext(ctx, &a, `
		SELECT id, release_id, original_name, remote_basename, storage_path, size, sha256, created_at
		FROM packages_packageartifact WHERE release_id = ? AND remote_basename = ?`, releaseID, basename)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &a, nil
}

func (r *Repos) DeleteArtifact(ctx context.Context, id int64) (int64, error) {
	res, err := r.db.ExecContext(ctx, `DELETE FROM packages_packageartifact WHERE id = ?`, id)
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}

func (r *Repos) UpdateArtifactFile(ctx context.Context, id int64, originalName, storagePath string, size int64, sha256 string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE packages_packageartifact
		SET original_name = ?, storage_path = ?, size = ?, sha256 = ?, updated_at = datetime('now')
		WHERE id = ?`,
		originalName, storagePath, size, sha256, id)
	return err
}

func (r *Repos) ReleaseCreatedBy(ctx context.Context, releaseID int64) (*int64, error) {
	var cb sql.NullInt64
	err := r.db.GetContext(ctx, &cb, `SELECT created_by_id FROM packages_packagerelease WHERE id = ?`, releaseID)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if !cb.Valid {
		return nil, nil
	}
	v := cb.Int64
	return &v, nil
}
