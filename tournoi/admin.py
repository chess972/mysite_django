from django.contrib import admin
from .models import Competition, Club, Match

# The simple way to register models
admin.site.register(Competition)
admin.site.register(Club)

# The "Pro" way to register the Match model to make your life easier
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    # These columns will show up in the main list view
    list_display = ('id', 'competition', 'status', 'score_team1', 'score_team2')

    # This creates a filter sidebar on the right side of the screen!
    list_filter = ('competition', 'status')

    # This adds a search bar at the top to search by Match ID
    search_fields = ('id',)
