<!-- Register page — Mind AI -->
<template>
  <div class="register-page">
    <div class="register-card">
      <!-- Left brand panel -->
      <div class="card-left">
        <div class="brand-area">
          <div class="brand-icon">🧠</div>
          <h1 class="brand-name">Mind</h1>
          <p class="brand-desc">加入图形可视化智能管理平台</p>
          <div class="brand-tags">
            <span>无限画布</span>
            <span>AI 助手</span>
            <span>云端存储</span>
          </div>
        </div>
      </div>

      <!-- Right form panel -->
      <div class="card-right">
        <div class="form-header">
          <h2>创建账户</h2>
          <p>注册后即可使用全部功能</p>
        </div>
        <a-form
          ref="formRef"
          :model="form"
          :rules="rules"
          layout="vertical"
          @finish="onSubmit"
        >
          <a-form-item name="username" label="用户名">
            <a-input
              v-model:value="form.username"
              placeholder="3-20 位字母、数字或下划线"
              size="large"
              autocomplete="username"
            >
              <template #prefix><UserOutlined /></template>
            </a-input>
          </a-form-item>
          <a-form-item name="password" label="密码">
            <a-input-password
              v-model:value="form.password"
              placeholder="至少 8 位，含大小写字母、数字和特殊字符"
              size="large"
              autocomplete="new-password"
            >
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>
          <a-form-item name="passwordConfirm" label="确认密码">
            <a-input-password
              v-model:value="form.passwordConfirm"
              placeholder="请再次输入密码"
              size="large"
              autocomplete="new-password"
            >
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>
          <a-form-item name="captcha" label="验证码">
            <div class="captcha-row">
              <a-input
                v-model:value="form.captcha"
                placeholder="请输入验证码"
                size="large"
                :maxlength="4"
                style="flex: 1"
              >
                <template #prefix><SafetyOutlined /></template>
              </a-input>
              <img
                v-if="randCodeData.requestCodeSuccess"
                :src="randCodeData.randCodeImage"
                class="captcha-img"
                title="点击刷新验证码"
                @click="initAuthCaptcha"
              />
              <div v-else class="captcha-placeholder">加载中</div>
            </div>
          </a-form-item>
          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              size="large"
              block
              :loading="submitting"
              class="submit-btn"
            >
              注册
            </a-button>
          </a-form-item>
        </a-form>
        <div class="form-footer">
          已有账户？
          <router-link to="/login" class="link">前往登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import {
  UserOutlined,
  LockOutlined,
  SafetyOutlined,
} from "@ant-design/icons-vue";
import { useAuthCaptcha } from "@/composables/useAuthCaptcha";
import { apiRegister } from "@/api/user";

const router = useRouter();
const { randCodeData, initAuthCaptcha } = useAuthCaptcha();

const formRef = ref();
const submitting = ref(false);

const form = reactive({
  username: "",
  password: "",
  passwordConfirm: "",
  captcha: "",
});

const validatePasswordConfirm = (_rule: any, value: string) => {
  if (!value) return Promise.reject("请确认密码");
  if (value !== form.password) return Promise.reject("两次输入的密码不一致");
  return Promise.resolve();
};

const rules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    {
      pattern: /^[a-zA-Z0-9_]{3,20}$/,
      message: "用户名只能包含字母、数字和下划线，长度 3-20",
      trigger: "blur",
    },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 8, message: "密码至少 8 个字符", trigger: "blur" },
  ],
  passwordConfirm: [
    { required: true, message: "请确认密码", trigger: "blur" },
    { validator: validatePasswordConfirm, trigger: "blur" },
  ],
  captcha: [
    { required: true, message: "请输入验证码", trigger: "blur" },
    { len: 4, message: "验证码为 4 位", trigger: "blur" },
  ],
};

async function onSubmit() {
  submitting.value = true;
  try {
    const formData = new FormData();
    formData.append("username", form.username);
    formData.append("password", form.password);
    formData.append("captcha", form.captcha);
    formData.append("captcha_id", randCodeData.captcha_id);

    await apiRegister(formData);
    message.success("注册成功，请登录");
    router.push("/login");
  } catch (err: any) {
    initAuthCaptcha();
    form.captcha = "";
  } finally {
    submitting.value = false;
  }
}
</script>

<style lang="scss" scoped>
$primary: #22c55e;

.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #11998e 0%, #22c55e 100%);
  padding: 20px;
}

.register-card {
  display: flex;
  width: 780px;
  max-width: 100%;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.card-left {
  width: 320px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #16a34a, #22c55e);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 30px;

  .brand-area {
    text-align: center;
    color: #fff;
  }
  .brand-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }
  .brand-name {
    font-size: 28px;
    font-weight: 800;
    margin: 0 0 8px;
    color: #fff;
  }
  .brand-desc {
    font-size: 14px;
    opacity: 0.9;
    margin-bottom: 20px;
  }
  .brand-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: center;
    span {
      padding: 4px 12px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.15);
      font-size: 12px;
    }
  }
}

.card-right {
  flex: 1;
  padding: 36px 36px;
  display: flex;
  flex-direction: column;
  justify-content: center;

  .form-header {
    margin-bottom: 24px;
    h2 {
      font-size: 22px;
      font-weight: 700;
      color: #1e293b;
      margin: 0 0 4px;
    }
    p {
      color: #64748b;
      font-size: 14px;
      margin: 0;
    }
  }

  .captcha-row {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .captcha-img {
    height: 40px;
    width: 100px;
    border-radius: 6px;
    cursor: pointer;
    border: 1px solid #e2e8f0;
    &:hover {
      border-color: $primary;
    }
  }
  .captcha-placeholder {
    height: 40px;
    width: 100px;
    border-radius: 6px;
    background: #f1f5f9;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    color: #94a3b8;
  }

  .submit-btn {
    height: 42px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    background: $primary;
    border: none;
    &:hover {
      background: #15803d;
    }
  }

  // Override browser autofill background
  :deep(input:-webkit-autofill),
  :deep(input:-webkit-autofill:hover),
  :deep(input:-webkit-autofill:focus) {
    -webkit-box-shadow: 0 0 0 1000px #fff inset;
    box-shadow: 0 0 0 1000px #fff inset;
    -webkit-text-fill-color: #1e293b;
    caret-color: #1e293b;
    transition: background-color 5000s ease-in-out 0s;
  }

  .form-footer {
    text-align: center;
    font-size: 13px;
    color: #64748b;
    margin-top: 8px;
    .link {
      color: #22c55e;
      font-weight: 500;
      text-decoration: none;
    }
  }
}

@media (max-width: 640px) {
  .register-card {
    flex-direction: column;
  }
  .card-left {
    width: 100%;
    padding: 24px 20px;
  }
  .card-right {
    padding: 24px 20px;
  }
}
</style>
