package repository

import (
	"context"
	"database/sql"
	"errors"
)

type User struct {
	ID           int64  `db:"id"`
	Username     string `db:"username"`
	Email        string `db:"email"`
	PasswordHash string `db:"password"`
	Role         string `db:"role"`
	IsActive     int    `db:"is_active"` // SQLite 0/1
}

func (r *Repos) GetUserByUsername(ctx context.Context, username string) (*User, error) {
	var u User
	err := r.db.GetContext(ctx, &u, `
		SELECT id, username, email, password, role, is_active
		FROM auth_user WHERE username = ? LIMIT 1`, username)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &u, nil
}

func (r *Repos) GetUserByID(ctx context.Context, id int64) (*User, error) {
	var u User
	err := r.db.GetContext(ctx, &u, `
		SELECT id, username, email, password, role, is_active
		FROM auth_user WHERE id = ? LIMIT 1`, id)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &u, nil
}

func (r *Repos) CreateUser(ctx context.Context, username, email, passwordHash, role string) (int64, error) {
	res, err := r.db.ExecContext(ctx, `
		INSERT INTO auth_user (password, username, email, role, is_active, date_joined, created_at, updated_at)
		VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'), datetime('now'))`,
		passwordHash, username, email, role)
	if err != nil {
		return 0, err
	}
	id, err := res.LastInsertId()
	return id, err
}

func (r *Repos) UpdateLastLoginIP(ctx context.Context, userID int64, ip string) error {
	_, err := r.db.ExecContext(ctx, `UPDATE auth_user SET last_login_ip = ?, updated_at = datetime('now') WHERE id = ?`, ip, userID)
	return err
}
