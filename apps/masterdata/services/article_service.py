"""Service layer for article business logic."""
from __future__ import annotations

from masterdata.repositories.article_repository import (
    create_article,
    delete_article_if_eligible,
    get_article_by_id,
    list_articles_by_compte,
    update_article,
)


def get_article_for_edit(article_id: int):
    """Fetch article or raise DoesNotExist."""
    return get_article_by_id(article_id)


def create_article_for_user(user, validated_data: dict):
    """Create an article, binding it to the user's compte."""
    validated_data["compte"] = user.compte
    return create_article(**validated_data)


def try_delete_article(article_id: int) -> tuple[bool, str]:
    """Attempt to delete an article.

    Returns (success, message).
    """
    art = get_article_by_id(article_id)
    if delete_article_if_eligible(art):
        return True, "Article deleted successfully"
    return False, "Cannot delete article. Quantity received is not equal to the original quantity."
