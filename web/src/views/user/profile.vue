<!-- Profile page — user info + change password -->
<template>
  <div class="profile-page">
    <div class="profile-header">
      <router-link to="/" class="back-link">← 返回</router-link>
      <h1>个人中心</h1>
    </div>

    <div class="profile-content">
      <a-tabs v-model:activeKey="activeTab">
        <!-- Basic Info Tab -->
        <a-tab-pane key="info" tab="基本信息">
          <a-form layout="vertical" class="info-form">
            <a-form-item label="用户名">
              <a-input v-model:value="profile.username" disabled />
            </a-form-item>
            <a-form-item label="邮箱">
              <a-input v-model:value="profile.email" placeholder="请输入邮箱" />
            </a-form-item>
            <a-form-item label="注册时间">
              <a-input :value="profile.created_at || '-'" disabled />
            </a-form-item>
            <a-form-item label="最后登录">
              <a-input :value="profile.last_login || '-'" disabled />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" :loading="savingProfile" @click="onSaveProfile"> 保存 </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <!-- Change Password Tab -->
        <a-tab-pane key="password" tab="修改密码">
          <a-form
            ref="pwdFormRef"
            :model="pwdForm"
            :rules="pwdRules"
            layout="vertical"
            class="pwd-form"
            @finish="onChangePassword"
          >
            <a-form-item name="oldPassword" label="原密码">
              <a-input-password
                v-model:value="pwdForm.oldPassword"
                placeholder="请输入原密码"
                autocomplete="current-password"
              />
            </a-form-item>
            <a-form-item name="newPassword" label="新密码">
              <a-input-password
                v-model:value="pwdForm.newPassword"
                placeholder="至少 8 位，含大小写字母、数字和特殊字符"
                autocomplete="new-password"
              />
            </a-form-item>
            <a-form-item name="confirmPassword" label="确认新密码">
              <a-input-password
                v-model:value="pwdForm.confirmPassword"
                placeholder="请再次输入新密码"
                autocomplete="new-password"
              />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="changingPwd"> 修改密码 </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/store/modules/user'

const userStore = useUserStore()
const activeTab = ref('info')
const savingProfile = ref(false)
const changingPwd = ref(false)
const pwdFormRef = ref()

const profile = reactive({
  username: '',
  email: '',
  created_at: '',
  last_login: '',
})

const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validatePwdConfirm = (_rule: any, value: string) => {
  if (!value) return Promise.reject('请确认新密码')
  if (value !== pwdForm.newPassword) return Promise.reject('两次输入的密码不一致')
  return Promise.resolve()
}

const pwdRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码长度 8-128 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validatePwdConfirm, trigger: 'blur' },
  ],
}

onMounted(async () => {
  try {
    await userStore.fetchProfile()
    const info = userStore.getUserInfo
    if (info) {
      profile.username = info.username || ''
      profile.email = info.email || ''
      profile.created_at = info.created_at || ''
      profile.last_login = info.last_login || ''
    }
  } catch {
    /* ignore */
  }
})

async function onSaveProfile() {
  savingProfile.value = true
  try {
    await userStore.updateProfile({ email: profile.email })
    message.success('保存成功')
  } catch {
    /* handled by interceptor */
  } finally {
    savingProfile.value = false
  }
}

async function onChangePassword() {
  changingPwd.value = true
  try {
    await userStore.changePassword({
      old_password: pwdForm.oldPassword,
      new_password: pwdForm.newPassword,
    })
    message.success('密码修改成功')
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
    pwdFormRef.value?.resetFields()
  } catch {
    /* handled by interceptor */
  } finally {
    changingPwd.value = false
  }
}
</script>

<style lang="scss" scoped>
.profile-page {
  min-height: 100vh;
  background: #f8fafc;
}

.profile-header {
  background: #fff;
  padding: 16px 32px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 16px;

  .back-link {
    color: #4f46e5;
    text-decoration: none;
    font-size: 14px;
    &:hover {
      text-decoration: underline;
    }
  }
  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #1e293b;
  }
}

.profile-content {
  max-width: 520px;
  margin: 24px auto;
  background: #fff;
  border-radius: 12px;
  padding: 24px 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

  .info-form,
  .pwd-form {
    max-width: 400px;
  }
}
</style>
