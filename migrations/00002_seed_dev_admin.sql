-- +goose Up
-- +goose StatementBegin
-- 开发用默认管理员（密码: admin）；生产环境请删除或改密后部署。
INSERT OR IGNORE INTO auth_user (id, password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, role, created_at, updated_at)
VALUES (
  1,
  'pbkdf2_sha256$260000$devsalt123456789012$Ld8z53YCu6cCL0xLZWRBHjyWjvhxViUALJ6Mt1SYF78=',
  1,
  'admin',
  '',
  '',
  'admin@localhost',
  1,
  1,
  datetime('now'),
  'admin',
  datetime('now'),
  datetime('now')
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DELETE FROM auth_user WHERE id = 1 AND username = 'admin';
-- +goose StatementEnd
