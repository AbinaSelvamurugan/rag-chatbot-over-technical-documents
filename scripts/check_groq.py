"""Explicitly check model access without making a paid generation request."""
from backend.app.core.config import settings

def main():
    cfg=settings()
    if not cfg.groq_api_key or not cfg.groq_model:
        raise SystemExit('GROQ_API_KEY and GROQ_MODEL must be configured')
    from groq import Groq
    client=Groq(api_key=cfg.groq_api_key,timeout=cfg.groq_timeout,max_retries=2)
    names={m.id for m in client.models.list().data}
    if cfg.groq_model not in names:
        raise SystemExit(f'Configured model {cfg.groq_model} is not in account model list')
    print(f'PASS: configured model {cfg.groq_model} is listed for this account')

if __name__=='__main__':main()
