# Topic 模块模型
from .topic import Topic
from .topic_prerequisite import TopicPrerequisite
from .topic_core_concept import TopicCoreConcept
from .topic_derivative import TopicDerivative
from .topic_extension import TopicExtension
from .topic_evaluation_anchor import TopicEvaluationAnchor
from .topic_similar_question import TopicSimilarQuestion
from .topic_advanced_question import TopicAdvancedQuestion
from .topic_reference import TopicReference
from .topic_review_log import TopicReviewLog

# User 模块模型
from .user import User
from .user_profile import UserProfile
from .user_topic_progress import UserTopicProgress
from .user_level import UserLevel

# System 模块模型
from .menu import Menu

# Prompt 模块模型
from .prompt_template import PromptTemplate
from .prompt_call_log import PromptCallLog, AgentTrace

# Outbox 补偿表
from .outbox import Outbox

# Quota 配额表
from .user_quota import UserQuota

# Captcha 验证码表
from .captcha import Captcha

# 用户-题目状态
from .user_topic_status import UserTopicStatus

# 岗位表
from .job_position import JobPosition

__all__ = [
    # Topic
    "Topic",
    "TopicPrerequisite",
    "TopicCoreConcept",
    "TopicDerivative",
    "TopicExtension",
    "TopicEvaluationAnchor",
    "TopicSimilarQuestion",
    "TopicAdvancedQuestion",
    "TopicReference",
    "TopicReviewLog",
    # User
    "User",
    "UserProfile",
    "UserTopicProgress",
    "UserLevel",
    # System
    "Menu",
    # Prompt
    "PromptTemplate",
    "PromptCallLog",
    "AgentTrace",
    # Outbox
    "Outbox",
    # Quota
    "UserQuota",
    "Captcha",
    "UserTopicStatus",
    "JobPosition",
]
