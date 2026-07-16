from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "interview_room" ADD COLUMN "session_state" JSONB;
        ALTER TABLE "interview_room" ADD COLUMN "version" INT NOT NULL DEFAULT 0;
        ALTER TABLE "interview_room" ADD COLUMN "expires_at" TIMESTAMPTZ;
        CREATE INDEX "idx_interview_room_owner_expiry"
            ON "interview_room" ("user_id", "expires_at");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_interview_room_owner_expiry";
        ALTER TABLE "interview_room" DROP COLUMN "expires_at";
        ALTER TABLE "interview_room" DROP COLUMN "version";
        ALTER TABLE "interview_room" DROP COLUMN "session_state";
    """
