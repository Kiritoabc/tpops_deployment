package db

import (
	"fmt"
	"path/filepath"

	"github.com/jmoiron/sqlx"
	"github.com/pressly/goose/v3"
	_ "modernc.org/sqlite"
)

// Open 打开 SQLite（modernc 驱动名 "sqlite"）。
func Open(dsn string) (*sqlx.DB, error) {
	db, err := sqlx.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return db, nil
}

// RunMigrations 执行 goose SQL（目录不存在则跳过并报错）。
func RunMigrations(db *sqlx.DB, dir string) error {
	goose.SetBaseFS(nil)
	abs, err := filepath.Abs(dir)
	if err != nil {
		return fmt.Errorf("migrations dir: %w", err)
	}
	if err := goose.SetDialect("sqlite3"); err != nil {
		return err
	}
	return goose.Up(db.DB, abs)
}
