package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"tpops_deployment/internal/auth"
)

const CtxUserID = "user_id"

func JWTAuth(secret string) gin.HandlerFunc {
	return func(c *gin.Context) {
		h := c.GetHeader("Authorization")
		if h == "" || !strings.HasPrefix(strings.ToLower(h), "bearer ") {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"detail": "未认证"})
			return
		}
		raw := strings.TrimSpace(h[7:])
		claims, err := auth.ParseToken(secret, raw)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"detail": "令牌无效或已过期"})
			return
		}
		c.Set(CtxUserID, claims.UserID)
		c.Next()
	}
}
