# -*- coding: UTF-8 -*-
"""Agent TTS — ChatTTS 语音合成服务，CPU 推理，带文件缓存。"""

import hashlib
import logging
import os
import re
import threading

from app.config import TTS_CACHE_DIR, TTS_ENABLED, TTS_MAX_TEXT_LENGTH, TTS_VOICE_SEED

logger = logging.getLogger(__name__)


class AgentTTS:
    """ChatTTS 封装 — 延迟加载、文本缓存、线程安全。

    Usage:
        tts = AgentTTS()
        audio_path = tts.generate("你好世界")
        # audio_path -> "<TTS_CACHE_DIR>/a1b2c3d4.wav"
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, cache_dir: str | None = None):
        self._cache_dir = cache_dir or TTS_CACHE_DIR
        self._model = None
        self._model_lock = threading.Lock()
        self._load_attempted = False

    # ── lazy singleton access ──────────────────────────────────────────────

    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── model loading ──────────────────────────────────────────────────────

    def _ensure_model(self):
        """延迟加载 ChatTTS 模型（首次调用时触发）。"""
        if self._model is not None:
            return
        if self._load_attempted:
            raise RuntimeError("ChatTTS 模型加载已失败，不再重试。请检查依赖。")

        with self._model_lock:
            if self._model is not None:
                return
            self._load_attempted = True

            try:
                import ChatTTS as _ChatTTS
                import torch

                logger.info("AgentTTS: 加载 ChatTTS 模型 (CPU) ...")
                chat = _ChatTTS.Chat()
                chat.load(compile=False)  # CPU 模式
                self._model = chat
                self._chattts = _ChatTTS
                self._torch = torch
                logger.info("AgentTTS: 模型加载完成")
            except ImportError as e:
                logger.error("AgentTTS: ChatTTS / torch 未安装 — %s", e)
                raise RuntimeError("ChatTTS 未安装，请运行: pip install ChatTTS torch") from e
            except Exception as e:
                logger.exception("AgentTTS: 模型加载失败")
                raise RuntimeError(f"ChatTTS 加载失败: {e}") from e

    # ── public API ─────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return TTS_ENABLED

    def generate(self, text: str) -> str:
        """将文本转为语音文件。

        Args:
            text: 要合成的文本（过长自动截断）。

        Returns:
            音频文件的绝对路径 (.wav)。

        Raises:
            ValueError: 文本为空。
            RuntimeError: 模型未就绪或推理失败。
        """
        if not TTS_ENABLED:
            raise RuntimeError("TTS 功能已禁用 (TTS_ENABLED=false)")

        cleaned = self._clean_text(text)
        if not cleaned:
            raise ValueError("text 为空或仅有标点符号")

        # 截断过长的文本
        if len(cleaned) > TTS_MAX_TEXT_LENGTH:
            logger.info("AgentTTS: 文本过长 (%d → %d)", len(cleaned), TTS_MAX_TEXT_LENGTH)
            cleaned = cleaned[:TTS_MAX_TEXT_LENGTH]

        # 检查缓存
        cache_key = self._cache_key(cleaned)
        cached_path = self._cache_path(cache_key)
        if os.path.exists(cached_path):
            logger.info("AgentTTS: 缓存命中 %s", cache_key)
            return cached_path

        # 推理
        self._ensure_model()
        os.makedirs(self._cache_dir, exist_ok=True)

        try:
            # ChatTTS 推理 — 参考官方示例
            # infer 返回 wavs 列表，每个元素是 (sample_rate, audio_data) 或直接是 numpy array
            _ChatTTS = self._chattts
            rnd_spk_emb = self._model.sample_random_speaker()
            params_infer_code = _ChatTTS.Chat.InferCodeParams(
                spk_emb=rnd_spk_emb,
                temperature=0.3,
                top_P=0.7,
                top_K=20,
            )
            params_refine_text = _ChatTTS.Chat.RefineTextParams(prompt="")

            wavs = self._model.infer(
                [cleaned],
                params_refine_text=params_refine_text,
                params_infer_code=params_infer_code,
                use_decoder=True,
                skip_refine_text=False,
            )

            if not wavs or len(wavs) == 0:
                raise RuntimeError("ChatTTS 推理返回空结果")

            audio_data = wavs[0]
            # audio_data 是 (sample_rate, numpy_array) 元组
            if isinstance(audio_data, tuple):
                sample_rate, audio_np = audio_data
            else:
                audio_np = audio_data

            # 保存为 WAV
            import numpy as np
            import scipy.io.wavfile as wavfile

            # 归一化到 int16
            if audio_np.dtype != np.int16:
                audio_np = (audio_np * 32767).astype(np.int16)

            wavfile.write(cached_path, 24000, audio_np)
            logger.info("AgentTTS: 生成完成 %s (%.1f KB)", cache_key, os.path.getsize(cached_path) / 1024)
            return cached_path

        except ImportError:
            raise RuntimeError("ChatTTS 依赖缺失 (numpy/scipy)，请运行: pip install numpy scipy")
        except Exception as e:
            logger.exception("AgentTTS: 推理失败")
            # 清理可能产生的半截文件
            if os.path.exists(cached_path):
                try:
                    os.remove(cached_path)
                except OSError:
                    pass
            raise RuntimeError(f"TTS 生成失败: {e}") from e

    # ── helpers ────────────────────────────────────────────────────────────

    def _clean_text(self, text: str) -> str:
        """清洗文本 — 去掉 Markdown 格式字符、多余空白。"""
        if not text:
            return ""
        # 移除 HTML/Markdown
        cleaned = re.sub(r"</?[^>]+(>|$)", "", text)
        cleaned = re.sub(r"[*_~>`#\[\]|]", "", cleaned)
        # 合并连续空白
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _cache_key(self, text: str) -> str:
        """文本 → MD5 hash。"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> str:
        """缓存 key → 文件路径。"""
        return os.path.join(self._cache_dir, f"{key}.wav")

    def url_for(self, filepath: str) -> str:
        """本地文件路径 → 对外可访问的 URL。"""
        filename = os.path.basename(filepath)
        return f"/v1/agent/tts/audio/{filename}"


# ── 清理过期缓存 ──────────────────────────────────────────────────────────────


def cleanup_tts_cache(max_files: int = 500) -> int:
    """清理 TTS 缓存目录，保留最近的 max_files 个文件。返回删除数量。"""
    if not os.path.isdir(TTS_CACHE_DIR):
        return 0
    files = [os.path.join(TTS_CACHE_DIR, f) for f in os.listdir(TTS_CACHE_DIR) if f.endswith(".wav")]
    if len(files) <= max_files:
        return 0
    files.sort(key=os.path.getmtime)
    to_remove = files[: len(files) - max_files]
    for f in to_remove:
        try:
            os.remove(f)
        except OSError:
            pass
    return len(to_remove)
