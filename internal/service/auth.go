package service

import (
	"context"
	"errors"
	"net/http"

	"tpops_deployment/internal/auth"
)

type LoginIn struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type LoginOut struct {
	Token struct {
		Access  string `json:"access"`
		Refresh string `json:"refresh"`
	} `json:"token"`
	User UserOut `json:"user"`
}

type UserOut struct {
	ID       int64  `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
	Role     string `json:"role"`
}

type RegisterIn struct {
	Username        string `json:"username"`
	Password        string `json:"password"`
	PasswordConfirm string `json:"password_confirm"`
	Email           string `json:"email"`
	Role            string `json:"role"`
}

func (s *Service) Login(ctx context.Context, in LoginIn, remoteIP string) (*LoginOut, int, error) {
	if in.Username == "" || in.Password == "" {
		return nil, http.StatusBadRequest, errors.New("需要提供用户名和密码")
	}
	u, err := s.repos.GetUserByUsername(ctx, in.Username)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if u == nil {
		return nil, http.StatusBadRequest, errors.New("用户名或密码错误")
	}
	if u.IsActive == 0 {
		return nil, http.StatusBadRequest, errors.New("用户已被禁用")
	}
	ok, err := auth.CheckPassword(in.Password, u.PasswordHash)
	if err != nil || !ok {
		return nil, http.StatusBadRequest, errors.New("用户名或密码错误")
	}
	_ = s.repos.UpdateLastLoginIP(ctx, u.ID, remoteIP)

	access, err := auth.SignAccess(s.cfg.JWTSecret, u.ID, u.Username, u.Role)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	refresh, err := auth.SignRefresh(s.cfg.JWTSecret, u.ID, u.Username, u.Role)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	out := &LoginOut{}
	out.Token.Access = access
	out.Token.Refresh = refresh
	out.User = UserOut{ID: u.ID, Username: u.Username, Email: u.Email, Role: u.Role}
	return out, http.StatusOK, nil
}

func (s *Service) Register(ctx context.Context, in RegisterIn) (int64, *UserOut, int, error) {
	if in.Password != in.PasswordConfirm {
		return 0, nil, http.StatusBadRequest, errors.New("密码不一致")
	}
	if in.Username == "" || in.Password == "" {
		return 0, nil, http.StatusBadRequest, errors.New("用户名和密码必填")
	}
	role := in.Role
	if role == "" {
		role = "viewer"
	}
	if u, err := s.repos.GetUserByUsername(ctx, in.Username); err != nil {
		return 0, nil, http.StatusInternalServerError, err
	} else if u != nil {
		return 0, nil, http.StatusBadRequest, errors.New("用户名已存在")
	}
	hash, err := auth.EncodePBKDF2Password(in.Password)
	if err != nil {
		return 0, nil, http.StatusInternalServerError, err
	}
	id, err := s.repos.CreateUser(ctx, in.Username, in.Email, hash, role)
	if err != nil {
		return 0, nil, http.StatusBadRequest, err
	}
	return id, &UserOut{ID: id, Username: in.Username, Email: in.Email, Role: role}, http.StatusCreated, nil
}

func (s *Service) Profile(ctx context.Context, userID int64) (*UserOut, error) {
	u, err := s.repos.GetUserByID(ctx, userID)
	if err != nil || u == nil {
		return nil, err
	}
	return &UserOut{ID: u.ID, Username: u.Username, Email: u.Email, Role: u.Role}, nil
}
