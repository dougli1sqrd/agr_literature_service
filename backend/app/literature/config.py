from typing import Optional

from pydantic import BaseSettings, Field


class GlobalConfig(BaseSettings):
    """Global configurations."""

    # This variable will be loaded from the .env file. However, if there is a
    # shell environment variable having the same name, that will take precedence.

    # the class Field is necessary while defining the global variables
    ENV_STATE: Optional[str] = Field(..., env="ENV_STATE")
    HOST: Optional[str] = Field(..., env="HOST")

    # environment specific configs
    API_USERNAME: Optional[str] = None
    API_PASSWORD: Optional[str] = None

    AUTH0_DOMAIN: Optional[str] = None
    AUTH0_API_AUDIENCE: Optional[str] = None

    PSQL_USERNAME: Optional[str] = None
    PSQL_PASSWORD: Optional[str] = None
    PSQL_HOST: Optional[str] = None
    PSQL_PORT: Optional[str] = None
    PSQL_DATABASE: Optional[str] = None

    class Config:
        """Loads the dotenv file."""

        env_file: str = ".env"

class DevConfig(GlobalConfig):
    """Development configurations."""

    class Config:
        env_prefix: str = ""


class ProdConfig(GlobalConfig):
    """Production configurations."""

    class Config:
        env_prefix: str = "PROD_"


class FactoryConfig:
    """Returns a config instance dependending on the ENV_STATE variable."""

    def __init__(self, env_state: Optional[str]):
        self.env_state = env_state

    def __call__(self):
        if self.env_state == "dev":
            return DevConfig()

        elif self.env_state == "prod":
            return ProdConfig()


config = FactoryConfig(GlobalConfig().ENV_STATE)()
