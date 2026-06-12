from tortoise import fields
from tortoise.models import Model

from src.models.fields import CompatibleJSONField


class Topic(Model):
    """面试题主表"""

    id = fields.UUIDField(pk=True)
    topic = fields.CharField(max_length=255)
    alias = CompatibleJSONField(null=True)
    domain = fields.CharField(max_length=100)
    tech_domain = fields.CharField(max_length=100, null=True)
    category = fields.CharField(max_length=100, null=True)
    tags = CompatibleJSONField(null=True)
    difficulty = fields.IntField(default=1)
    mastery_level = fields.IntField(default=0)
    review_count = fields.IntField(default=0)
    keywords = CompatibleJSONField(null=True)

    core_summary = fields.TextField(null=True)
    one_liner = fields.CharField(max_length=200, null=True)
    core_points = fields.TextField(null=True)
    detailed_explanation = fields.TextField(null=True)

    agent_instructions_a = fields.TextField(null=True)
    agent_instructions_b = fields.TextField(null=True)
    agent_instructions_c = fields.TextField(null=True)

    code_example = fields.TextField(null=True)
    traps = fields.TextField(null=True)
    bonuses = fields.TextField(null=True)
    
    # 向量字段（用于语义相似度搜索）
    embedding_vector = fields.TextField(null=True)
    
    status = fields.CharField(max_length=32, default="ACTIVE")

    last_reviewed = fields.DatetimeField(null=True)
    next_review = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 一对多关系
    prerequisites: fields.ReverseRelation["TopicPrerequisite"]
    core_concepts: fields.ReverseRelation["TopicCoreConcept"]
    derivatives: fields.ReverseRelation["TopicDerivative"]
    extensions: fields.ReverseRelation["TopicExtension"]
    evaluation_anchors: fields.ReverseRelation["TopicEvaluationAnchor"]
    similar_questions: fields.ReverseRelation["TopicSimilarQuestion"]
    advanced_questions: fields.ReverseRelation["TopicAdvancedQuestion"]
    references: fields.ReverseRelation["TopicReference"]
    review_logs: fields.ReverseRelation["TopicReviewLog"]

    class Meta:
        table = "topic"
        schema = "public"

    def __str__(self):
        return f"Topic({self.id}, {self.topic})"
