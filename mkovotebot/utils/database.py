from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Optional
import logging

import aiosqlite as aiosqlite

from mkovotebot import settings

logger = logging.getLogger(__name__)
PATH = settings.DATABASE_PATH


@dataclass
class Candidate:
    discord_id: int
    votes_count: int


# I know that using ;f-strings in SQL queries is not allowed, but I did not find another way
# Also self._table is a checked value, so the chance of SQL injection is 0%.


class MKODatabase:
    def __init__(self, table: str):
        if table not in ["mko_votes", "president_votes"]:
            raise ValueError(f"{table} table is not allowed")
        self._table = table

    async def setup(self):
        """
        Create database if not exist
        """
        logger.debug("[%s] Setting up database", self._table)

        query = f"""
        CREATE TABLE IF NOT EXISTS {self._table}
        (
            voter_id     integer not null,
            candidate_id integer not null,
            unique (voter_id)
        );
        """
        async with aiosqlite.connect(PATH) as db:
            await db.execute(query)
            await db.commit()

    async def set_user_vote(self, voter_id: int, candidate_id: Optional[int]):
        logger.debug(
            "[%s] set_user_vote is called with %s / %s",
            self._table,
            voter_id,
            candidate_id,
        )
        async with aiosqlite.connect(PATH) as db:
            if candidate_id is not None:
                await db.execute(
                    f"""INSERT INTO {self._table}(voter_id, candidate_id) VALUES(?, ?)
           ON CONFLICT(voter_id) DO UPDATE SET candidate_id=?""",
                    (
                        voter_id,
                        candidate_id,
                        candidate_id,
                    ),
                )
            else:
                await db.execute(
                    f"""DELETE FROM {self._table} WHERE voter_id = ?""",
                    (voter_id,),
                )

            await db.commit()

    async def reset_candidate_votes(self, candidate_id: int) -> List[int]:
        logger.debug(
            "[%s] reset_candidate_votes is called with %s",
            self._table,
            candidate_id,
        )
        candidate_votes = await self.get_candidate_votes(candidate_id)
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                f"""DELETE FROM {self._table} WHERE candidate_id = ?""",
                (candidate_id,),
            )

            await db.commit()
        return candidate_votes

    async def get_user_vote(self, voter_id: int) -> Optional[int]:
        logger.debug("[%s] get_user_vote is called with %s", self._table, voter_id)
        async with aiosqlite.connect(PATH) as db:
            async with db.execute(
                f"""SELECT candidate_id FROM {self._table} WHERE voter_id = ?""",
                (voter_id,),
            ) as cursor:
                if vote := await cursor.fetchone():
                    return vote[0]
                else:
                    return None

    async def get_candidate_votes(self, candidate_id: int) -> List[int]:
        logger.debug(
            "[%s] get_candidate_votes is called with %s",
            self._table,
            candidate_id,
        )
        async with aiosqlite.connect(PATH) as db:
            async with db.execute(
                f"""SELECT voter_id FROM {self._table} WHERE candidate_id = ?""",
                (candidate_id,),
            ) as cursor:
                return [voter[0] for voter in await cursor.fetchall()]

    async def get_candidates(self) -> List[Candidate]:
        logger.debug(
            "[%s] get_candidates is called",
            self._table,
        )

        async with aiosqlite.connect(PATH) as db:
            async with db.execute(
                f"""SELECT candidate_id, COUNT(*) FROM {self._table} GROUP BY candidate_id""",
            ) as cursor:
                candidates = [
                    Candidate(discord_id=raw_candidate[0], votes_count=raw_candidate[1])
                    for raw_candidate in await cursor.fetchall()
                ]
                candidates.sort(key=lambda c: c.votes_count, reverse=True)
                return candidates

    async def clear_all_votes(self):
        logger.warning(
            "[%s] clear_all_votes is called ",
            self._table,
        )
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                f"""DELETE FROM {self._table}""",
            )
            await db.commit()


class PresidentElectionsDatabase(MKODatabase):
    def __init__(self):
        super().__init__(table="president_votes")



class MKOVotingDatabase(MKODatabase):
    def __init__(self):
        super().__init__(table="mko_votes")
