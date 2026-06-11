<template>
  <div class="legal-page">
    <h1>隐私协议</h1>
    <p class="update-date">最后更新：2026 年 6 月</p>

    <section>
      <h2>一、信息收集</h2>
      <p>思量（以下简称"本平台"）在提供服务过程中，可能收集以下信息：</p>
      <ul>
        <li><strong>账户信息</strong>：注册时提供的用户名、邮箱地址、加密后的登录密码；</li>
        <li><strong>学习偏好</strong>：您选择的目标岗位、学习偏好方向、经验水平、每日学习目标；</li>
        <li><strong>模拟面试相关</strong>：您上传的简历文件、输入的岗位描述（JD）、面试过程中的对话记录；</li>
        <li><strong>使用数据</strong>：题目浏览记录、掌握状态标记、Agent 对话次数等平台使用行为数据。</li>
      </ul>
    </section>

    <section>
      <h2>二、信息使用</h2>
      <p>收集的信息用于以下目的：</p>
      <ul>
        <li>为您推荐适合当前水平和岗位的面试题；</li>
        <li>提供个性化的模拟面试体验；</li>
        <li>分析学习进度，生成掌握度报告；</li>
        <li>改进平台服务质量和用户体验。</li>
      </ul>
      <p><strong>本平台不会将您的个人信息出售、交易或以其他方式转让给第三方</strong>，除非获得您的明确同意或法律要求。</p>
    </section>

    <section>
      <h2>三、信息存储与安全</h2>
      <ul>
        <li>您的账户密码使用 bcrypt 加密存储，平台无法获取明文密码；</li>
        <li>简历和 JD 文件在模拟面试结束后，系统默认保留 7 天后自动删除。您可以在用户中心手动提前删除；</li>
        <li>平台采用 PostgreSQL 数据库存储数据，数据库仅限应用服务访问，不对外开放端口；</li>
        <li>所有数据传输通过 HTTPS 加密。</li>
      </ul>
    </section>

    <section>
      <h2>四、用户权利</h2>
      <ul>
        <li><strong>查阅权</strong>：您可以在用户中心查看已收集的个人信息；</li>
        <li><strong>更正权</strong>：您可以随时修改学习偏好、目标岗位等信息；</li>
        <li><strong>删除权</strong>：您可以通过用户中心删除简历、JD 文件及面试记录；</li>
        <li><strong>注销权</strong>：您可以联系管理员注销账户，注销后所有个人数据将被永久删除。</li>
      </ul>
    </section>

    <section>
      <h2>五、Cookie 与本地存储</h2>
      <p>本平台使用浏览器 localStorage 存储 JWT 身份令牌和用户偏好标识，不使用第三方 Cookie 或追踪脚本。</p>
    </section>

    <section>
      <h2>六、免责声明</h2>
      <ul>
        <li>模拟面试中的 AI 回答仅供参考学习，不构成职业建议；</li>
        <li>用户上传的简历和 JD 仅用于当前模拟面试会话，平台不对简历内容进行人工审核；</li>
        <li>因不可抗力（如服务器故障、网络攻击）导致的数据丢失，平台不承担责任，但会尽力恢复。</li>
      </ul>
    </section>

    <section>
      <h2>七、协议更新</h2>
      <p>本协议可能不定期更新，更新后将在平台公示。继续使用本平台即视为同意更新后的协议。</p>
    </section>

    <section>
      <h2>八、联系方式</h2>
      <p>如有隐私相关问题，请联系：<strong>siLiang@support.com</strong></p>
    </section>
  </div>
</template>

<style scoped>
.legal-page {
  max-width: 800px; margin: 0 auto; padding: 40px 24px;
  font-size: 15px; line-height: 1.8; color: #333;
}
h1 { font-size: 28px; font-weight: 800; margin: 0 0 4px; }
.update-date { color: #999; font-size: 13px; margin: 0 0 32px; }
h2 { font-size: 18px; font-weight: 700; margin: 32px 0 12px; color: #1a1a2e; }
p { margin: 0 0 12px; }
ul { padding-left: 20px; margin: 0 0 16px; }
li { margin-bottom: 6px; }
strong { color: #1a1a2e; }
</style>
