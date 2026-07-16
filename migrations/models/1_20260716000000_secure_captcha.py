from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "captcha" ADD COLUMN "code_hash" VARCHAR(64) NOT NULL DEFAULT '';
        ALTER TABLE "captcha" ADD COLUMN "purpose" VARCHAR(32) NOT NULL DEFAULT 'captcha';
        ALTER TABLE "captcha" ADD COLUMN "target" VARCHAR(255);
        ALTER TABLE "captcha" ADD COLUMN "attempts" INT NOT NULL DEFAULT 0;
        ALTER TABLE "captcha" DROP COLUMN "code";
        ALTER TABLE "captcha" ALTER COLUMN "code_hash" DROP DEFAULT;
        CREATE INDEX "idx_captcha_purpose_target_created"
            ON "captcha" ("purpose", "target", "created_at");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_captcha_purpose_target_created";
        ALTER TABLE "captcha" ADD COLUMN "code" VARCHAR(8) NOT NULL DEFAULT '';
        ALTER TABLE "captcha" DROP COLUMN "attempts";
        ALTER TABLE "captcha" DROP COLUMN "target";
        ALTER TABLE "captcha" DROP COLUMN "purpose";
        ALTER TABLE "captcha" DROP COLUMN "code_hash";
    """
