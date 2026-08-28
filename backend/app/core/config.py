from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://corvinus:corvinus@localhost:5432/corvinus"
    database_url_sync: str = "postgresql://corvinus:corvinus@localhost:5432/corvinus"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "super-secret-jwt-key-for-demo-only"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "corvinus-files"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
