-- +goose Up
-- +goose StatementBegin
ALTER TABLE deployment_deploymenttask ADD COLUMN use_raw_shell INTEGER NOT NULL DEFAULT 0;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 1;
-- +goose StatementEnd
