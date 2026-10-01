from pathlib import Path
from typing import Optional

from app.services.cache.task_cache import TaskCache
from app.enums.task_status_enums import TaskStatus
from app.gpt.base import GPT
from app.gpt.gpt_factory import GPTFactory
from app.models.model_config import ModelConfig
from app.models.notes_model import NoteResult
from app.models.pipeline_model import PreparedTask
from app.services.postprocessing import PostProcessor
from app.formatters import get_formatter
from app.utils.note_helper import append_top_comments
from app.utils.logger import get_logger
from app.config.model_config_manager import get_model_config

logger = get_logger(__name__)


class AIProcessor:
    """AI 处理阶段：GPT 总结、后处理、保存笔记"""

    def __init__(self, image_output_dir: str, image_base_url: str):
        self.post_processor = PostProcessor(image_output_dir, image_base_url)

    def process(
        self, prepared: PreparedTask, model_name: Optional[str] = None
    ) -> Optional[NoteResult]:
        task_id = prepared.task_id

        try:
            logger.info(f"开始 AI 处理 (task_id={task_id})")
            gpt = self._get_gpt(model_name)

            # GPT 总结
            TaskCache.update_status(task_id, TaskStatus.SUMMARIZING)
            markdown = gpt.summarize(prepared.gpt_source)

            # 后处理：截图 & 链接替换
            if prepared.formats:
                markdown = self.post_processor.process(
                    markdown=markdown,
                    formats=prepared.formats,
                    video_path=prepared.video_path,
                    video_id=prepared.audio_meta.video_id,
                    platform=prepared.platform,
                )

            # 笔记格式化挂件：markdown 保留来源链接+信息卡；obsidian 生成
            # frontmatter + 一级标题（screenshot/link 标记替换已在上方完成）
            markdown = get_formatter(prepared.note_format).decorate(markdown, prepared)

            # 追加热门评论尾部（仅 B 站）
            if prepared.platform == "bilibili":
                from app.utils.bilibili_meta import fetch_top_comments
                top_comments = fetch_top_comments(prepared.audio_meta.video_id)
                markdown = append_top_comments(markdown, top_comments)

            # 保存笔记到最终路径
            final_path = self._resolve_output_path(prepared)
            Path(final_path).parent.mkdir(parents=True, exist_ok=True)
            Path(final_path).write_text(markdown, encoding="utf-8")
            logger.info(f"笔记已保存: {final_path}")

            # 保存元数据
            logger.info(f"开始保存笔记 (task_id={task_id})")
            TaskCache.update_status(task_id, TaskStatus.SAVING)
            TaskCache.save_metadata(
                video_id=prepared.audio_meta.video_id,
                platform=prepared.platform,
                task_id=task_id,
            )

            TaskCache.update_status(task_id, TaskStatus.SUCCESS)
            logger.info(f"笔记生成成功 (task_id={task_id})")
            return NoteResult(
                markdown=markdown,
                transcript=prepared.transcript,
                audio_meta=prepared.audio_meta,
                output_path=final_path,
            )

        except Exception as exc:
            logger.error(f"AI 处理失败 (task_id={task_id})：{exc}", exc_info=True)
            TaskCache.update_status(task_id, TaskStatus.FAILED, message=str(exc))
            return None

    @staticmethod
    def _resolve_output_path(prepared: PreparedTask) -> str:
        """确定笔记最终落盘路径。

        目录跟随 prepared.output_path 所在目录（用户通过 --output-dir 或批次目录
        指定，未指定时为默认笔记目录）；文件名统一为
        "{标题[:50]} - {作者[:20]} - {视频ID}.md"，作者缺失时省略该段，
        视频 ID 与标题相同（local 平台）时跳过；标题缺失时回退 task_id 命名。
        """
        if prepared.output_path:
            out_dir = Path(prepared.output_path).parent
        else:
            from app.utils.path_helper import get_path_manager
            out_dir = Path(get_path_manager().output_notes_dir)

        audio_meta = prepared.audio_meta
        if audio_meta:
            raw_info = audio_meta.raw_info or {}
            title = (audio_meta.title or raw_info.get("title") or "").strip()
            author = (raw_info.get("uploader") or raw_info.get("author") or "").strip()
            video_id = audio_meta.video_id or ""
            if title:
                from app.utils.bilibili_meta import sanitize_filename
                # 标题/作者截断以约束文件名长度，视频 ID 保持在末尾便于检索
                segments = [sanitize_filename(title)[:50]]
                if author:
                    segments.append(sanitize_filename(author)[:20])
                if video_id and video_id != title:
                    segments.append(video_id)
                return str(out_dir / f"{' - '.join(segments)}.md")

        if prepared.output_path:
            return prepared.output_path

        from app.utils.path_helper import get_path_manager
        return get_path_manager().get_note_output_path(prepared.task_id)

    @staticmethod
    def _get_gpt(model_name: Optional[str]) -> GPT:
        model_config = get_model_config(model_name)
        if not model_config:
            logger.error(f"[get_gpt] 无法加载模型配置: model_name={model_name}")
            raise RuntimeError(f"无法加载模型 '{model_name}' 的配置，请检查环境变量")

        logger.info(f"创建 GPT 实例: {model_name}")
        config = ModelConfig(
            api_key=model_config["api_key"],
            base_url=model_config["base_url"],
            model_name=model_config["model_name"],
            provider="openai",
            name=model_name,
        )
        return GPTFactory().from_config(config)
