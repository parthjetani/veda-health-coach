from fastapi import Depends, Request

from app.config import Settings, get_settings


def get_supabase(request: Request):
    return request.app.state.supabase


def get_http_client(request: Request):
    return request.app.state.http_client


def get_anthropic_client(request: Request):
    return request.app.state.anthropic_client


def get_settings_dep() -> Settings:
    return get_settings()
