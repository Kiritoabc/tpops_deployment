// TPOPS Go 服务入口（go-dev）：Gin + SQLite，与 Python 版 API 前缀对齐。
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Kiritoabc/tpops_deployment/go/internal/config"
	"github.com/Kiritoabc/tpops_deployment/go/internal/db"
	"github.com/Kiritoabc/tpops_deployment/go/internal/handler"
	"github.com/Kiritoabc/tpops_deployment/go/internal/middleware"
	"github.com/Kiritoabc/tpops_deployment/go/internal/repository"
	"github.com/Kiritoabc/tpops_deployment/go/internal/service"
	"github.com/Kiritoabc/tpops_deployment/go/internal/wshub"
	"github.com/gin-gonic/gin"
)

func main() {
	cfg := config.Load()
	sqlDB, err := db.Open(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("db: %v", err)
	}
	defer sqlDB.Close()

	if err := db.RunMigrations(sqlDB, cfg.MigrationsDir); err != nil {
		log.Fatalf("migrations: %v", err)
	}

	repos := repository.New(sqlDB)
	hub := wshub.NewHub()
	svc := service.New(repos, cfg, hub)
	h := handler.New(svc, cfg, hub)

	if cfg.GinMode != "" {
		gin.SetMode(cfg.GinMode)
	}
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(middleware.RequestID())
	r.Use(middleware.CORS())

	h.Register(r)

	srv := &http.Server{
		Addr:              cfg.Listen,
		Handler:           r,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       0,
		WriteTimeout:      0,
	}

	go func() {
		log.Printf("tpops-go listening on %s (sqlite)", cfg.Listen)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("shutdown: %v", err)
	}
}
