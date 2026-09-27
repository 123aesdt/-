import time
import os
import threading
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from avatars.base_avatar import BaseAvatar
from utils.logger import logger

# Built-in LLM providers. Each exposes an OpenAI-compatible chat completions
# endpoint; the active one is selected with --llm_provider (default: dashscope).
LLM_PROVIDERS = {
    "dashscope": {
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "orcarouter": {
        "api_key_env": "ORCAROUTER_API_KEY",
        "base_url": "https://api.orcarouter.ai/v1",
        "default_model": "orcarouter/auto",
    },
}

_LOCAL_QWEN_CACHE = {}
_LOCAL_QWEN_LOCK = threading.Lock()


def _llm_provider(opt) -> str:
    """Return the configured provider name, defaulting to dashscope."""
    return getattr(opt, 'llm_provider', 'dashscope') or 'dashscope'


def _llm_client(opt):
    """Create the OpenAI-compatible client for the configured provider."""
    from openai import OpenAI
    cfg = LLM_PROVIDERS.get(_llm_provider(opt), LLM_PROVIDERS['dashscope'])
    return OpenAI(
        api_key=os.getenv(cfg['api_key_env']),
        base_url=cfg['base_url'],
    )


def _llm_model(opt) -> str:
    """Resolve the model name, falling back to the provider default."""
    cfg = LLM_PROVIDERS.get(_llm_provider(opt), LLM_PROVIDERS['dashscope'])
    return getattr(opt, 'llm_model', '') or cfg['default_model']


def _load_local_qwen(model_path: str):
    """Load and cache a local Qwen model for in-process inference."""
    cached = _LOCAL_QWEN_CACHE.get(model_path)
    if cached:
        return cached

    with _LOCAL_QWEN_LOCK:
        cached = _LOCAL_QWEN_CACHE.get(model_path)
        if cached:
            return cached

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        dtype = torch.float16 if device == 'cuda' else torch.float32
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            local_files_only=True,
            dtype=dtype,
        ).to(device).eval()
        cached = (tokenizer, model, device)
        _LOCAL_QWEN_CACHE[model_path] = cached
        logger.info(f"local Qwen loaded: {model_path} on {device}")
        return cached


def _generate_local_qwen(message: str, opt) -> str:
    """Generate one concise Chinese answer with the locally deployed Qwen."""
    import torch

    model_path = getattr(opt, 'llm_model', '') or os.getenv(
        'LOCAL_QWEN_MODEL', '/root/autodl-tmp/dir'
    )
    tokenizer, model, device = _load_local_qwen(model_path)
    prompt = tokenizer.apply_chat_template(
        [
            {
                'role': 'system',
                'content': (
                    '你是一名中文医疗健康咨询助手。回答要简洁、自然、便于口播；'
                    '只提供一般健康信息，不做确诊，遇到急症或高风险情况提醒用户及时就医。'
                ),
            },
            {'role': 'user', 'content': message},
        ],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer([prompt], return_tensors='pt')
    inputs = {name: tensor.to(device) for name, tensor in inputs.items()}
    prompt_length = inputs['input_ids'].shape[1]
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(output[0][prompt_length:], skip_special_tokens=True).strip()


def llm_response(message,avatar_session:'BaseAvatar',datainfo:dict={}):
    try:
        opt = avatar_session.opt
        start = time.perf_counter()
        if _llm_provider(opt) == 'local_qwen':
            answer = _generate_local_qwen(message, opt)
            if answer:
                logger.info(f"local Qwen response: {answer}")
                avatar_session.put_msg_txt(answer, datainfo)
            logger.info(f"local Qwen total time: {time.perf_counter()-start}s")
            return

        client = _llm_client(opt)
        model = _llm_model(opt)
        end = time.perf_counter()
        logger.info(f"llm Time init: {end-start}s,{message}")
        completion = client.chat.completions.create(
            model=model,
            messages=[{'role': 'system', 'content': '你是一个知识助手，尽量以简短、口语化的方式输出'},
                    {'role': 'user', 'content': message}],
            stream=True,
            # Display token usage in the last line of the streamed response.
            stream_options={"include_usage": True}
        )
        result=""
        first = True
        for chunk in completion:
            if len(chunk.choices)>0:
                #print(chunk.choices[0].delta.content)
                if first:
                    end = time.perf_counter()
                    logger.info(f"llm Time to first chunk: {end-start}s")
                    first = False
                msg = chunk.choices[0].delta.content
                if msg is None:
                    continue
                lastpos=0
                #msglist = re.split('[,.!;:，。！?]',msg)
                for i, char in enumerate(msg):
                    if char in ",.!;:，。！？：；" :
                        result = result+msg[lastpos:i+1]
                        lastpos = i+1
                        if len(result)>10:
                            logger.info(result)
                            avatar_session.put_msg_txt(result,datainfo)
                            result=""
                result = result+msg[lastpos:]
        end = time.perf_counter()
        logger.info(f"llm Time to last chunk: {end-start}s")
        if result:
            avatar_session.put_msg_txt(result,datainfo)

    except Exception as e:
        logger.exception('llm exceptiopn:')
        return
