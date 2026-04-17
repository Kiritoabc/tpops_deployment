// TPOPS 服务入口：Gin + SQLite + 内嵌静态页。
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"tpops_deployment/internal/config"
	"tpops_deployment/internal/db"
	"tpops_deployment/internal/handler"
	"tpops_deployment/internal/middleware"
	"tpops_deployment/internal/repository"
	"tpops_deployment/internal/service"
	"tpops_deployment/internal/wshub"
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
