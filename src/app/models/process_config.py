"""ProcessConfig - CLI 处理参数配置，统一替代手工参数拆解"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.enmus.note_enums import DownloadQuality


class ProcessConfig(BaseModel):
    """处理参数配置包。

    收拢 CLI ``process`` / ``search`` 子命令的所有共享参数，
    通过 ``ProcessConfig(**vars(args))`` 一键从 argparse namespace 转换。
    """

    model_config = ConfigDict(extra="ignore")

    quality: DownloadQuality = Field(default=DownloadQuality.medium)
    screenshot: bool = False
    link: bool = False
    style: str | None = None
    format: list[str] = Field(default_factory=list)
    video_understanding: bool = False
    video_interval: int = 0
    grid_size: list[int] | None = None
    no_subtitle: bool = False
    extras: str | None = None

    @field_validator("quality", mode="before")
    @classmethod
    def parse_quality(cls, v: object) -> DownloadQuality:
        if isinstance(v, DownloadQuality):
            return v
        if isinstance(v, str):
            mapping = {
                "fast": DownloadQuality.fast,
                "medium": DownloadQuality.medium,
                "slow": DownloadQuality.slow,
            }
            if v in mapping:
                return mapping[v]
        return DownloadQuality.medium

    @model_validator(mode="after")
    def sync_format_from_flags(self):
        """将 screenshot/link 布尔标志同步到 format 列表"""
        fmt = list(self.format) if self.format else []
        if self.screenshot and "screenshot" not in fmt:
            fmt.append("screenshot")
        if self.link and "link" not in fmt:
            fmt.append("link")
        self.format = fmt
        return self
