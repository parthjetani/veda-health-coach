from supabase import Client


def get_supabase_client(app) -> Client:
    return app.state.supabase
