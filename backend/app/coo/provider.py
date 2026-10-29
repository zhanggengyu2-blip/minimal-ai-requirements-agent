"""Server-side OpenAI-compatible Chat Completions / Tool Calling adapter."""
import httpx
from dataclasses import dataclass
from app.core.config import get_settings
from app.core.exceptions import AppError

@dataclass
class ChatResult:
    message: dict
    token_usage: int|None

class ModelClient:
    def __init__(self, settings=None): self.settings=settings or get_settings()

    async def complete(self, messages, *, tools=None, timeout=None, max_tokens=None):
        s=self.settings
        if not s.coo_api_key or not s.coo_model:
            raise AppError('Coo 模型未配置，请在服务端设置 COO_API_KEY、COO_BASE_URL 与 COO_MODEL',code='COO_MODEL_NOT_CONFIGURED',status_code=503)
        payload={'model':s.coo_model,'messages':messages,'temperature':0,'max_tokens':max_tokens or s.coo_max_output_tokens,
                 'response_format':{'type':'json_object'}}
        if tools:payload.update(tools=tools,tool_choice='auto')
        try:
            async with httpx.AsyncClient(timeout=min(timeout or s.coo_timeout_seconds,s.coo_timeout_seconds),follow_redirects=False) as client:
                response=await client.post(s.coo_base_url.rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+s.coo_api_key},json=payload)
            response.raise_for_status();data=response.json();choice=data['choices'][0];message=choice['message']
            if not isinstance(message,dict) or choice.get('finish_reason') not in ('stop','tool_calls',None): raise ValueError()
            if message.get('tool_calls'):
                calls=message['tool_calls']
                if not isinstance(calls,list) or not 1<=len(calls)<=5: raise ValueError()
                ids=[]
                for call in calls:
                    if not isinstance(call,dict) or call.get('type')!='function' or not isinstance(call.get('id'),str) or not isinstance(call.get('function'),dict):raise ValueError()
                    if not isinstance(call['function'].get('name'),str) or not isinstance(call['function'].get('arguments'),str):raise ValueError()
                    ids.append(call['id'])
                if len(set(ids))!=len(ids):raise ValueError()
            elif not isinstance(message.get('content'),str):raise ValueError()
            total=data.get('usage',{}).get('total_tokens')
            if type(total) is not int or total<0: total=None
            # Retain only protocol fields; never log headers or credentials.
            return ChatResult({k:v for k,v in message.items() if k in ('role','content','tool_calls')},total)
        except httpx.TimeoutException:
            raise AppError('Coo 模型调用超时，请稍后重试',code='COO_MODEL_TIMEOUT',status_code=503) from None
        except (httpx.HTTPError,ValueError,KeyError,TypeError,IndexError):
            raise AppError('Coo 模型请求失败或返回格式不完整，请检查模型服务配置',code='COO_MODEL_ERROR',status_code=503) from None
