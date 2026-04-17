package service

import "errors"

var (
	ErrForbidden      = errors.New("forbidden")
	ErrNoCredential   = errors.New("no_credential")
	ErrNoManifestYAML = errors.New("no_manifest_yaml")
)

// ManifestNotSupported 当前任务 action 不轮询 manifest。
type ManifestNotSupported struct{ Action string }

func (e ManifestNotSupported) Error() string { return "action_not_manifest" }
