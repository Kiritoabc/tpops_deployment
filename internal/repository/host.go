package repository

type Host struct {
	ID                int64  `db:"id"`
	Name              string `db:"name"`
	Hostname          string `db:"hostname"`
	Port              int    `db:"port"`
	Username          string `db:"username"`
	AuthMethod        string `db:"auth_method"`
	Credential        string `db:"credential"`
	DockerServiceRoot string `db:"docker_service_root"`
	CreatedByID       *int64 `db:"created_by_id"`
	CreatedAt         string `db:"created_at"`
	UpdatedAt         string `db:"updated_at"`
}
