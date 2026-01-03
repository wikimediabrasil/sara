from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from users.models import UserProfile, TeamArea, Position

"""
Custom Django admin configuration for User.

- Replaces the default User admin to conditionally include UserProfile inline.
- UserProfile is shown only on edit, not on user creation.
"""


class UserProfileInline(admin.StackedInline):
    """Inline profile shown when editing an existing User."""
    model = UserProfile
    can_delete = False


class AccountUserAdmin(AuthUserAdmin):
    """
    Custom UserAdmin that hides profile inline on add_view
    to avoid errors when UserProfile does not yet exist.
    """

    def add_view(self, *args, **kwargs):
        # No inlines when creating a new user
        self.inlines = []
        return super(AccountUserAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        # Show UserProfile inline when editing
        self.inlines = [UserProfileInline]
        return super(AccountUserAdmin, self).change_view(*args, **kwargs)


admin.site.unregister(User)
admin.site.register(User, AccountUserAdmin)
admin.site.register(TeamArea)
admin.site.register(Position)
