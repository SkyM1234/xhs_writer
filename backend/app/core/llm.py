"""
LLM 客户端封装
"""
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logger import logger
import asyncio
import os


class LLMClient:
    """LLM 客户端统一接口"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

        # 初始化客户端
        if self.provider == "qwen":
            self.client = AsyncOpenAI(
                api_key=os.environ.get("QWEN_API_KEY"),
                base_url=settings.LLM_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        elif self.provider == "deepseek":
            self.client = AsyncOpenAI(
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
                base_url=settings.LLM_BASE_URL or "https://api.deepseek.com"
            )
        elif self.provider == "openai":
            self.client = AsyncOpenAI(
                # api_key=settings.LLM_API_KEY, # 从环境变量获取获取 API 密钥
                base_url=settings.LLM_BASE_URL
            )
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        model: Optional[str] = None
    ) -> str:
        """
        调用 LLM 进行对话（带重试机制）

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数（可选）
            max_tokens: 最大 token 数（可选）
            response_format: 响应格式（可选，如 {"type": "json_object"}）
            max_retries: 最大重试次数（默认3次）
            retry_delay: 重试延迟（秒，默认2秒）
            model: 指定模型（可选，默认使用配置的模型）

        Returns:
            LLM 响应内容
        """
        last_exception = None
        current_delay = retry_delay

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature or self.temperature,
                    "max_tokens": max_tokens or self.max_tokens
                }

                # think 模型不支持非流式调用，必须通过 extra_body 显式关闭 thinking 模式
                # "parameter.enable_thinking must be set to false for non-streaming calls"
                if model == "qwen3-32b" or model == "deepseek-v4-pro":
                    kwargs["extra_body"] = {"enable_thinking": False}

                # 添加响应格式（如果支持）
                if response_format:
                    kwargs["response_format"] = response_format

                # 打印输入到LLM的内容
                logger.info("\n" + "="*80)
                logger.info("🔵 LLM 输入")
                logger.info("="*80)
                logger.info(f"模型: {kwargs['model']}")
                logger.info(f"温度: {kwargs['temperature']}")
                logger.info(f"最大Token: {kwargs['max_tokens']}")
                if attempt > 0:
                    logger.warning(f"⚠️ 重试次数: {attempt}/{max_retries}")
                logger.info("\n消息内容:")
                for i, msg in enumerate(messages):
                    logger.info(f"\n[消息 {i+1}] 角色: {msg['role']}")
                    logger.info("-" * 40)
                    logger.info(msg['content'])
                logger.info("="*80 + "\n")

                response = await self.client.chat.completions.create(**kwargs)

                result = response.choices[0].message.content

                # 打印LLM的输出
                logger.info("\n" + "="*80)
                logger.info("🟢 LLM 输出")
                logger.info("="*80)
                logger.info(result)
                logger.info("="*80 + "\n")

                return result

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                logger.warning(f"⚠️ LLM 调用失败 (尝试 {attempt + 1}/{max_retries}): {error_type} - {str(e)}")

                if attempt < max_retries - 1:
                    logger.info(f"   等待 {current_delay:.1f}秒后重试...")
                    await asyncio.sleep(current_delay)
                    current_delay *= 2  # 指数退避
                else:
                    logger.error(f"   已达到最大重试次数，放弃重试")

        # 所有重试都失败
        raise Exception(f"LLM 调用失败（已重试{max_retries}次）: {str(last_exception)}")
    
    async def chat_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None
    ) -> str:
        """
        带系统提示词的对话

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            response_format: 响应格式
            model: 指定模型（可选，默认使用配置的模型）

        Returns:
            LLM 响应内容
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            model=model
        )


# 全局 LLM 客户端实例
llm_client = LLMClient()
