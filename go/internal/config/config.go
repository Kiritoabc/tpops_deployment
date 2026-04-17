package config

import (
	"path/filepath"
	"runtime"

	"github.com/caarlos0/env/v10"
)

// Config 从环境变量加载（十二因子）。
type Config struct {
	Listen        string `env:"TPOPS_GO_LISTEN" envDefault:":8081"`
	DatabaseURL   string `env:"TPOPS_GO_DATABASE_URL"` // 默认在 Load 中设置
	MigrationsDir string `env:"TPOPS_GO_MIGRATIONS_DIR"` // 默认在 Load 中设置
	JWTSecret     string `env:"TPOPS_GO_JWT_SECRET"`     // HS256，须与生产密钥区分
	GinMode       string `env:"TPOPS_GO_GIN_MODE" envDefault:"debug"`
}

func Load() Config {
	var c Config
	if err := env.Parse(&c); err != nil {
		panic(err)
	}
	_, file, _, _ := runtime.Caller(0)
	// internal/config -> repo root go/
	goRoot := filepath.Join(filepath.Dir(file), "..", "..")
	if c.MigrationsDir == "" {
		c.MigrationsDir = filepath.Join(goRoot, "migrations")
	}
	if c.DatabaseURL == "" {
		c.DatabaseURL = "file:" + filepath.Join(goRoot, "data", "tpops_go.db") + "?_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)"
	}
	if c.JWTSecret == "" {
		c.JWTSecret = "change-me-tpops-go-jwt-secret"
	}
	return c
}
