"""Cog-file for MKO voting"""
import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from mkovotebot import settings, config
from mkovotebot.utils import MKOVotingDatabase, database, api

logger = logging.getLogger(__name__)


# TODO: Automatic hourly hours check
# TODO: dynamic votes ☠


class MKOVoting(commands.Cog):
    """
    About
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot
        self.database = MKOVotingDatabase()

    async def update_voter(self, discord_id, avoid_circular_calls=False) -> bool:
        """
        Check voter - hours and player role

        :return - True if voter`s vote is active
        """
        plasmo_guild = self.bot.get_guild(config.PlasmoRPGuild.id)
        user = plasmo_guild.get_member(discord_id)
        candidate_id = await self.database.get_user_vote(discord_id)
        if candidate_id is None:
            return False

        if (
            user is None
            or plasmo_guild.get_role(config.PlasmoRPGuild.player_role_id)
            not in user.roles
        ):
            await self.database.set_user_vote(voter_id=discord_id, candidate_id=None)
            if not avoid_circular_calls:
                await self.update_candidate(candidate_id)
            return False

        played_hours = await api.get_player_hours(discord_id)
        if played_hours == -1:  # Plasmo API Error
            return True

        if played_hours < settings.Config.required_weekly_hours:
            await self.database.set_user_vote(voter_id=discord_id, candidate_id=None)
            await plasmo_guild.get_channel(config.PlasmoRPGuild.low_priority_announcement_channel_id).send(
                content=user.mention,
                embed=disnake.Embed(
                    color=disnake.Color.dark_red(),
                    title="❌ Ваш голос аннулирован",
                    description=f"Чтобы голосовать нужно наиграть "
                    f"хотя бы {settings.Config.required_weekly_hours} ч. за неделю \n "
                                f"||У вас - {round(played_hours, 2)} ч.||",
                ).set_thumbnail(url="https://rp.plo.su/avatar/" + user.display_name),
            )
            await self.update_candidate(candidate_id)
            return False

        return True

    async def update_candidate(self, discord_id) -> bool:
        """
        Check candidate - hours and player role

        :return - True if voter`s vote is active
        """
        votes = await self.database.get_candidate_votes(discord_id)
        user = self.bot.get_guild(config.PlasmoRPGuild.id).get_member(discord_id)
        if (
            user is None
            or user.guild.get_role(config.PlasmoRPGuild.player_role_id)
            not in user.roles
        ):
            await self.update_voter(discord_id, avoid_circular_calls=True)
            if len(votes) > 0:
                plasmo_user = await api.get_user(discord_id=discord_id)
                await self.bot.get_guild(config.PlasmoRPGuild.id).get_channel(
                    config.PlasmoRPGuild.announcement_channel_id
                    if len(votes) >= settings.Config.required_mko_votes
                    else config.PlasmoRPGuild.low_priority_announcement_channel_id
                ).send(
                    content=(", ".join([f"<@{user_id}>" for user_id in votes])),
                    embed=disnake.Embed(
                        color=disnake.Color.dark_red(),
                        title="❌ Голоса аннулированны",
                        description=f"У **{plasmo_user.nick if plasmo_user is not None else 'кандидата'}** "
                        f"нет роли игрока на Plasmo RP, все голоса аннулированы",
                    ).set_thumbnail(
                        url="https://rp.plo.su/avatar/"
                        + (plasmo_user.nick if plasmo_user is not None else "___")
                    ),
                )
            logger.debug("Unable to get %s, resetting all votes", discord_id)
            await self.database.reset_candidate_votes(discord_id)
            return False

        mko_member_role = user.guild.get_role(config.PlasmoRPGuild.mko_member_role_id)
        if len(votes) >= settings.Config.required_mko_votes:
            if mko_member_role not in user.roles:
                await user.add_roles(mko_member_role, reason="New MKO member")
                await user.guild.get_channel(
                    config.PlasmoRPGuild.announcement_channel_id
                ).send(
                    content=user.mention,
                    embed=disnake.Embed(
                        color=disnake.Color.dark_green(),
                        title="📃 Новый участник совета",
                        description=user.mention + " прошел в совет",
                    ).set_thumbnail(
                        url="https://rp.plo.su/avatar/" + user.display_name
                    ),
                )
            return True
        else:
            if mko_member_role in user.roles:
                await user.remove_roles(
                    mko_member_role, reason="Not enough votes to be MKO member"
                )
                await user.guild.get_channel(
                    config.PlasmoRPGuild.announcement_channel_id
                ).send(
                    content=user.mention,
                    embed=disnake.Embed(
                        color=disnake.Color.dark_red(),
                        title="❌ Игрок покидает совет",
                        description=user.mention
                        + " потерял голоса нужные для участия в совете",
                    ).set_thumbnail(
                        url="https://rp.plo.su/avatar/" + user.display_name
                    ),
                )
            return False

    @commands.slash_command(
        name="vote-top",
    )
    async def vote_top(
        self,
        inter: ApplicationCommandInteraction,
    ):
        """
        Получить топ игроков по голосам

        Parameters
        ----------
        inter: ApplicationCommandInteraction object
        """

        # TODO:
        #  get roles from db via mkovotebot.utils.database.get_candidates()
        #  create top, add buttons, use view to change pages
        ...

    @commands.slash_command(
        name="vote-info",
    )
    async def vote_info(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(lambda _: _.author),
    ):
        """
        Получить информацию об игроке

        Parameters
        ----------
        user: Игрок
        inter: ApplicationCommandInteraction object
        """

        if (
            user.guild.get_role(config.PlasmoRPGuild.player_role_id) not in user.roles
            or user.bot
        ):
            await self.update_candidate(user.id)
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.dark_red(),
                    title="❌ Ошибка",
                    description="Невозможно получить статистику у пользователя без проходки",
                ),
                ephemeral=True,
            )

        await inter.response.defer(ephemeral=True)
        await self.update_candidate(user.id)
        await self.update_voter(user.id)

        voted_user = await self.database.get_user_vote(user.id)
        if (
            voted_user is not None
            and await self.update_candidate(discord_id=voted_user) is True
        ):
            user_vote_string = f"Игрок проголосовал за <@{voted_user}>"
        else:
            user_vote_string = "Игрок ни за кого не проголосовал"

        voters_list = []
        for user_id in await self.database.get_candidate_votes(user.id):
            if not await self.update_voter(user_id):
                continue
            voters_list.append(f"<@{user_id}>")

        voters = await self.database.get_candidate_votes(user.id)

        user_info_embed = disnake.Embed(
            color=disnake.Color.dark_green(),
            title=f"Статистика {user.display_name} "
            + (
                settings.Config.member_emoji
                if len(voters) >= settings.Config.required_mko_votes
                else ""
            ),
            description=user_vote_string,
        )
        if len(voters):
            user_info_embed.add_field(
                name=f"За {user.display_name} проголосовало: {len(voters)}",
                value=", ".join(voters_list),
                inline=False,
            )
        await inter.edit_original_message(embed=user_info_embed)

    @commands.slash_command(
        name="fvote",
    )
    @commands.default_member_permissions(manage_roles=True)
    async def force_vote(
        self,
        inter: ApplicationCommandInteraction,
        voter: disnake.Member,
        candidate: disnake.Member,
    ):
        """
        Отдать голос игрока за другого игрока

        Parameters
        ----------
        voter: Избиратель
        candidate: ID Избираемый игрок
        inter: ApplicationCommandInteraction object
        """
        logger.info("%s called /fvote %s %s", inter.author.id, voter.id, candidate.id)
        # TODO: /fvote <member1> <member2>
        if voter == candidate:
            await inter.send(
                "Я тебе просто объясню как будет, я знаю, уже откуда ты, и вижу как ты подключен, "
                "я сейчас беру эту инфу и просто не поленюсь и пойду в полицию, и хоть у тебя и "
                "динамический iр , но Бай-флай хранит инфо 3 года, о запросах абонентов и их подключении, "
                "так что узнать у кого был IР в ото время дело пары минут, а дальше статья за разжигание "
                "межнациональной розни и о нормальной работе или учёбе да и о жизни, можешь забыть, "
                "мой тебе совет",
                ephemeral=True,
            )

        # Check old vote

        # Check hours

        # Write to db

        # Call update_candidate(id=candidate.id)
        ...

    @commands.slash_command(
        name="funvote",
    )
    @commands.default_member_permissions(manage_roles=True)
    async def force_unvote(
        self,
        inter: ApplicationCommandInteraction,
        voter: disnake.Member,
    ):
        """
        Снять голос игрока

        Parameters
        ----------
        voter: Избиратель
        inter: ApplicationCommandInteraction object
        """
        logger.info("%s called /funvote %s", inter.author.id, voter.id)
        # TODO: /funvote <member1> <member2>

        # Check old vote

        # Check hours

        # Write to db

        # Call update_candidate(id=candidate.id)
        ...

    async def cog_load(self):
        """
        Called when disnake cog is loaded
        """
        logger.info("%s Ready", __name__)


def setup(bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(MKOVoting(bot))
