from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "outbox" ADD COLUMN "next_retry_at" TIMESTAMPTZ;
        ALTER TABLE "outbox" ADD COLUMN "lease_until" TIMESTAMPTZ;
        ALTER TABLE "outbox" ADD COLUMN "worker_id" VARCHAR(64);
        ALTER TABLE "outbox" ADD COLUMN "idempotency_key" VARCHAR(128) UNIQUE;
        ALTER TABLE "outbox" ADD COLUMN "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        CREATE INDEX "idx_outbox_status_retry" ON "outbox" ("status", "next_retry_at");
        CREATE INDEX "idx_outbox_status_lease" ON "outbox" ("status", "lease_until");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_outbox_status_lease";
        DROP INDEX IF EXISTS "idx_outbox_status_retry";
        ALTER TABLE "outbox" DROP COLUMN "updated_at";
        ALTER TABLE "outbox" DROP COLUMN "idempotency_key";
        ALTER TABLE "outbox" DROP COLUMN "worker_id";
        ALTER TABLE "outbox" DROP COLUMN "lease_until";
        ALTER TABLE "outbox" DROP COLUMN "next_retry_at";
    """
