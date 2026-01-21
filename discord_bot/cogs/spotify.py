import atexit
import datetime as dt
import json

import discord
import requests
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks

from ..environment import DATA_DIR
from ..log_setup import logger
from ..utils import utils as ut

### @package misc
#
# Collection of miscellaneous helpers.
#

AIT_MUSIC_LIST = "https://raw.githubusercontent.com/xoundbyte/soul-over-ai/refs/heads/main/dist/artists.json"

SOUL_OVER_AI_ARTIST_BASE_URL = "https://souloverai.com/artist/{}"

ai_music_dict_listT = list[dict[str, str | float | dt.datetime]]

artist_stats_dictT = dict[str, dict[str, str | int]]

DISCLAIMER = "Please note that soul over ai is community driven. It is no proof for the artist beeing AI. They're just compiling evidence."


class SpotifyWatcher(commands.Cog):
    """Cog that watches Discord members' Spotify activity and notifies them about AI music artists."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the SpotifyWatcher cog."""
        super().__init__()

        self.bot: commands.Bot = bot
        self.ai_account_data_full: ai_music_dict_listT = []
        self.ai_account_names: dict[str, str] = {}

        self.update_ai_music_catalogue()

        self.reported_ai_incidents, self.artist_stats = self.load()

        atexit.register(self.store)

        self.fetch_ai_music_list_task.start()
        self.watch_members_task.start()

        # we use the user id to not enter a user multiple times,
        #  if they're member on multiple servers (different member objects, but same id)
        self.last_user_sent_account: dict[int, str] = {}

    def load(self) -> tuple[int, artist_stats_dictT]:
        """Load both incident count and artist statistics from disk."""
        # Load incident count
        count_path = DATA_DIR / "incident_count.txt"
        if not count_path.exists():
            incident_count = 0
        else:
            incident_count = int(count_path.read_text())

        # Load artist stats
        stats_path = DATA_DIR / "artist_stats.json"
        if not stats_path.exists():
            artist_stats: artist_stats_dictT = {}
        else:
            try:
                artist_stats = json.loads(stats_path.read_text())
            except json.JSONDecodeError:
                logger.warning("Failed to parse artist_stats.json, returning empty dict")
                artist_stats = {}

        return incident_count, artist_stats

    def store(self) -> None:
        """Store both incident count and artist statistics to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Store incident count
        count_path = DATA_DIR / "incident_count.txt"
        count_path.write_text(str(self.reported_ai_incidents))

        # Store artist stats
        stats_path = DATA_DIR / "artist_stats.json"
        stats_path.write_text(json.dumps(self.artist_stats, indent=2))

    def fetch_ai_music_list(self) -> ai_music_dict_listT | None:
        """Fetch the AI music artist list from the remote API."""
        r = requests.get(AIT_MUSIC_LIST)
        if r.status_code != 200:
            logger.warning(f"Failed to fetch AI music list: {r.status_code}")
            return None

        content = r.json()
        return content

    @staticmethod
    def _extract_account_names(data: ai_music_dict_listT) -> dict[str, str]:
        """Extract account names and IDs from the AI music data."""
        return {account["name"]: account["id"] for account in data}

    def update_ai_music_catalogue(self) -> None:
        """Update the local AI music catalogue from the remote API."""
        content = self.fetch_ai_music_list()
        if content is None:
            logger.warning("Failed to fetch AI music list, not updating list")
            return
        self.ai_account_data_full = content
        self.ai_account_names = self._extract_account_names(content)

    def current_listeners(self) -> list[tuple[discord.Member, discord.Spotify]]:
        """Get all members currently listening to Spotify across all guilds."""
        listeners: list[discord.Member] = []
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.activities:
                    continue
                for activity in member.activities:
                    if activity.type == discord.ActivityType.listening and activity.name == "Spotify":
                        listeners.append((member, activity))
        return listeners

    @tasks.loop(seconds=10)
    async def watch_members_task(self) -> None:
        """Task that watches members' Spotify activity and notifies them about AI artists."""
        logger.debug("Running task to watch members for AI music")
        listeners = self.current_listeners()

        new_incidents = 0
        for listener, spotify_state in listeners:
            if spotify_state.artist not in self.ai_account_names:
                continue

            account_name = spotify_state.artist
            account_id = self.ai_account_names[account_name]
            report_url = SOUL_OVER_AI_ARTIST_BASE_URL.format(account_id)

            # Update artist statistics
            current_time = dt.datetime.now(dt.timezone.utc).isoformat()
            if account_name not in self.artist_stats:
                self.artist_stats[account_name] = {"first detect": current_time, "total detects": 0}
            self.artist_stats[account_name]["total detects"] += 1

            if listener.id in self.last_user_sent_account and self.last_user_sent_account[listener.id] == account_name:
                continue

            msg = (
                "The artist you're currently listening to is listed on https://souloverai.com\n"
                f"You can find out more at: {report_url}"
            )
            emb = ut.make_embed(
                title="Potential AI Artist detected!",
                color=ut.red,
                name=f"{account_name} is on the Soul Over AI index",
                value=msg,
                footer=DISCLAIMER,
            )

            try:
                self.last_user_sent_account[listener.id] = account_name
                await ut.send_embed(listener, emb)

            # why this: because send_embed expects a ctx-object but itÄs first attempt can handle a user.
            # the error handling will fail , but I'm ignoring this for now
            except AttributeError:
                logger.info(f"Failed to message {listener.display_name} ({listener.id}), about {report_url}")

            new_incidents += 1

        if not new_incidents:
            return

        self.reported_ai_incidents += new_incidents
        logger.info(
            f"Reported {new_incidents} new incidents to users, total reported incidents: {self.reported_ai_incidents}"
        )

        self.store()

        await self.change_presence()

    async def change_presence(self):
        # Set bot activity to "reported {n} incidents to users"
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Reported {self.reported_ai_incidents} incidents. {len(self.ai_account_names)} AI accounts in database",
            ),
            status=discord.Status.do_not_disturb,
        )

    @tasks.loop(seconds=3600)
    async def fetch_ai_music_list_task(self) -> None:
        """Task that periodically updates the AI music catalogue."""
        logger.info("Running task to update AI music catalogue")
        self.update_ai_music_catalogue()
        await self.change_presence()

    @app_commands.command(name="about", description="Get the list of AI music artists")
    async def about_command(self, interaction: discord.Interaction) -> None:
        """Display information about the AI music watcher bot."""
        await interaction.response.send_message(
            embed=ut.make_embed(
                title="AI Music Watcher",
                color=ut.blue_light,
                name="Telling you when you listen to AI music",
                value="I will tell you via DM when you listen to an artist that is listed on https://souloverai.com as AI music artist.\n\n"
                "You can report an artist as AI music artist at https://souloverai.com/add artist command.\n\n"
                "I don't log your listening history, the only thing logged is when I attempt to notify you about an artist beeing potentiall AI and I can't send you a DM. "
                "In this case your user-name, your discord-id and the artist you listend to is logged with a timestamp.\n\n"
                "Please note the this bot is **not affiliated** with the soul over ai project, it is maintained by Chris (https://github.com/nonchris/discord-spotify-ai-detect)\n\n"
                "It aims to operate under the licensing terms of soul over ai (https://github.com/xoundbyte/soul-over-ai/blob/main/LICENSE.md)",
                footer=DISCLAIMER,
            )
        )


async def setup(bot: commands.Bot) -> None:
    """Setup function to add the SpotifyWatcher cog to the bot."""
    await bot.add_cog(SpotifyWatcher(bot))
