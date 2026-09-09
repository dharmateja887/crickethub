from django.test import TestCase
from .models import Player, Team


class TeamAndPlayerModelTests(TestCase):
    def test_team_and_player_can_be_created(self):
        team = Team.objects.create(
            name="Chennai Super Kings",
            city="Chennai",
            founded_year=2008,
        )
        player = Player.objects.create(
            name="MS Dhoni",
            team=team,
            jersey_number=7,
            position="Wicketkeeper",
            batting_style="Right-handed",
            bowling_style="Right-arm medium",
        )

        self.assertEqual(team.name, "Chennai Super Kings")
        self.assertEqual(player.team, team)
        self.assertEqual(player.name, "MS Dhoni")
