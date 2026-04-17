package repository

import "github.com/jmoiron/sqlx"

type Repos struct {
	db *sqlx.DB
}

func New(db *sqlx.DB) *Repos {
	return &Repos{db: db}
}

func (r *Repos) DB() *sqlx.DB { return r.db }
