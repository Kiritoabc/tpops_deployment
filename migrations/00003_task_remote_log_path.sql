-- +goose Up
-- +goose StatementBegin
ALTER TABLE deployment_deploymenttask ADD COLUMN remote_log_path VARCHAR(512) NOT NULL DEFAULT '';
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 1;
-- +goose StatementEnd
