<template>
  <div id="app">
    <div class="container">
      
      <!-- Dark overlay for better text readability -->
      <div v-if="!token" class="video-overlay"></div>

      <!-- Show title only if the user is not logged in (no token) -->
      <h1 v-if="!token" class="title">Weapon Detection Stream</h1>

      <!-- Login/Register Form -->
      <div v-if="!token" class="auth-form">
        <div class="form-toggle">
          <button 
            @click="isRegisterMode = false" 
            :class="{ active: !isRegisterMode }"
            class="toggle-btn"
          >
            Login
          </button>
          <button 
            @click="isRegisterMode = true" 
            :class="{ active: isRegisterMode }"
            class="toggle-btn"
          >
            Register
          </button>
        </div>

        <div class="input-container">
          <input
            v-model="username"
            placeholder="Username (min 3 characters)"
            class="input-field"
            :class="{ error: usernameError }"
            @input="clearErrors"
          />
          <input
            type="password"
            v-model="password"
            :placeholder="isRegisterMode ? 'Password (min 6 characters)' : 'Password'"
            class="input-field"
            :class="{ error: passwordError }"
            @input="clearErrors"
          />
          
          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
          <div v-if="successMessage" class="success-message">{{ successMessage }}</div>
          
          <button 
            @click="isRegisterMode ? register() : login()" 
            class="auth-btn"
            :disabled="isLoading"
          >
            {{ isLoading ? 'Please wait...' : (isRegisterMode ? 'Create Account' : 'Login') }}
          </button>
        </div>
      </div>

      <!-- Stream Container with User Menu -->
      <div v-else class="stream-container">
        <div class="user-header">
          <div class="user-info">
            <span class="username-display">Welcome, {{ currentUsername }}!</span>
            <span class="user-since" v-if="userCreatedAt">Member since: {{ formatDate(userCreatedAt) }}</span>
          </div>
          <div class="user-actions">
            <button @click="showChangePassword = true" class="action-btn change-password-btn">Change Password</button>
            <button @click="logout" class="action-btn logout-btn">Logout</button>
            <button @click="showDeleteConfirm = true" class="action-btn delete-btn">Delete Account</button>
          </div>
        </div>
        
        <h3 class="stream-title">Live AI Stream from rtsp!</h3>
        <img :src="videoUrl" class="video-stream" alt="AI Stream" />
      </div>

      <!-- Change Password Modal -->
      <div v-if="showChangePassword" class="modal-overlay" @click="closeChangePasswordModal">
        <div class="modal" @click.stop>
          <h3>Change Password</h3>
          <div class="password-form">
            <input
              type="password"
              v-model="currentPasswordInput"
              placeholder="Current Password"
              class="input-field"
              :class="{ error: changePasswordError }"
              @input="clearChangePasswordErrors"
            />
            <input
              type="password"
              v-model="newPasswordInput"
              placeholder="New Password (min 6 characters)"
              class="input-field"
              :class="{ error: changePasswordError }"
              @input="clearChangePasswordErrors"
            />
            <input
              type="password"
              v-model="confirmPasswordInput"
              placeholder="Confirm New Password"
              class="input-field"
              :class="{ error: changePasswordError }"
              @input="clearChangePasswordErrors"
            />
            
            <div v-if="changePasswordError" class="error-message">{{ changePasswordErrorMessage }}</div>
            <div v-if="changePasswordSuccess" class="success-message">{{ changePasswordSuccessMessage }}</div>
          </div>
          
          <div class="modal-actions">
            <button @click="closeChangePasswordModal" class="cancel-btn">Cancel</button>
            <button @click="changePassword" class="confirm-btn" :disabled="isLoading">
              {{ isLoading ? 'Changing...' : 'Change Password' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Delete Account Confirmation Modal -->
      <div v-if="showDeleteConfirm" class="modal-overlay" @click="showDeleteConfirm = false">
        <div class="modal" @click.stop>
          <h3>Delete Account</h3>
          <p>Are you sure you want to delete your account? This action cannot be undone.</p>
          <div class="modal-actions">
            <button @click="showDeleteConfirm = false" class="cancel-btn">Cancel</button>
            <button @click="deleteAccount" class="delete-confirm-btn" :disabled="isLoading">
              {{ isLoading ? 'Deleting...' : 'Yes, Delete My Account' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"

const username = ref("admin")
const password = ref("admin123")
const token = ref("")
const videoUrl = ref("")
const isRegisterMode = ref(false)
const errorMessage = ref("")
const successMessage = ref("")
const usernameError = ref(false)
const passwordError = ref(false)
const isLoading = ref(false)
const currentUsername = ref("")
const userCreatedAt = ref("")
const showDeleteConfirm = ref(false)

// Change password modal states
const showChangePassword = ref(false)
const currentPasswordInput = ref("")
const newPasswordInput = ref("")
const confirmPasswordInput = ref("")
const changePasswordError = ref(false)
const changePasswordErrorMessage = ref("")
const changePasswordSuccess = ref(false)
const changePasswordSuccessMessage = ref("")

onMounted(() => {
  // Force remove scrollbars with JavaScript
  document.documentElement.style.overflow = 'hidden'
  document.body.style.overflow = 'hidden'
  document.documentElement.style.height = '100%'
  document.body.style.height = '100%'
  document.documentElement.style.margin = '0'
  document.body.style.margin = '0'
  document.documentElement.style.padding = '0'
  document.body.style.padding = '0'

  // Check for existing token in localStorage
  const savedToken = localStorage.getItem('authToken')
  const savedUsername = localStorage.getItem('currentUsername')
  if (savedToken && savedUsername) {
    token.value = savedToken
    currentUsername.value = savedUsername
    videoUrl.value = `/api/video?token=${token.value}`
    fetchUserInfo()
  }
})

function clearErrors() {
  errorMessage.value = ""
  successMessage.value = ""
  usernameError.value = false
  passwordError.value = false
}

function clearChangePasswordErrors() {
  changePasswordError.value = false
  changePasswordErrorMessage.value = ""
  changePasswordSuccess.value = false
  changePasswordSuccessMessage.value = ""
}

function closeChangePasswordModal() {
  showChangePassword.value = false
  currentPasswordInput.value = ""
  newPasswordInput.value = ""
  confirmPasswordInput.value = ""
  clearChangePasswordErrors()
}

function validateInput() {
  let isValid = true
  
  if (username.value.trim().length < 3) {
    usernameError.value = true
    errorMessage.value = "Username must be at least 3 characters long"
    isValid = false
  }
  
  if (isRegisterMode.value && password.value.length < 6) {
    passwordError.value = true
    errorMessage.value = "Password must be at least 6 characters long"
    isValid = false
  }
  
  return isValid
}

function validatePasswordChange() {
  if (!currentPasswordInput.value) {
    changePasswordError.value = true
    changePasswordErrorMessage.value = "Please enter your current password"
    return false
  }
  
  if (newPasswordInput.value.length < 6) {
    changePasswordError.value = true
    changePasswordErrorMessage.value = "New password must be at least 6 characters long"
    return false
  }
  
  if (newPasswordInput.value !== confirmPasswordInput.value) {
    changePasswordError.value = true
    changePasswordErrorMessage.value = "New passwords do not match"
    return false
  }
  
  if (currentPasswordInput.value === newPasswordInput.value) {
    changePasswordError.value = true
    changePasswordErrorMessage.value = "New password must be different from current password"
    return false
  }
  
  return true
}

async function changePassword() {
  if (!validatePasswordChange()) return
  
  isLoading.value = true
  clearChangePasswordErrors()
  
  try {
    const res = await fetch("/api/change-password", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token.value}`
      },
      body: JSON.stringify({ 
        current_password: currentPasswordInput.value,
        new_password: newPasswordInput.value
      })
    })
    
    const data = await res.json()
    
    if (res.ok) {
      changePasswordSuccess.value = true
      changePasswordSuccessMessage.value = "Password changed successfully!"
      
      // Clear the form inputs
      currentPasswordInput.value = ""
      newPasswordInput.value = ""
      confirmPasswordInput.value = ""
      
      // Close modal after 2 seconds
      setTimeout(() => {
        closeChangePasswordModal()
      }, 2000)
    } else {
      changePasswordError.value = true
      changePasswordErrorMessage.value = data.error || "Failed to change password"
    }
  } catch (error) {
    changePasswordError.value = true
    changePasswordErrorMessage.value = "Network error. Please try again."
  }
  
  isLoading.value = false
}

async function login() {
  if (!validateInput()) return
  
  isLoading.value = true
  clearErrors()
  
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        username: username.value.trim(), 
        password: password.value 
      })
    })
    
    const data = await res.json()
    
    if (data.access_token) {
      token.value = data.access_token
      currentUsername.value = data.username
      videoUrl.value = `/api/video?token=${token.value}`
      
      // Save to localStorage
      localStorage.setItem('authToken', token.value)
      localStorage.setItem('currentUsername', currentUsername.value)
      
      fetchUserInfo()
    } else {
      errorMessage.value = data.error || "Login failed"
    }
  } catch (error) {
    errorMessage.value = "Network error. Please try again."
  }
  
  isLoading.value = false
}

async function register() {
  if (!validateInput()) return
  
  isLoading.value = true
  clearErrors()
  
  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        username: username.value.trim(), 
        password: password.value 
      })
    })
    
    const data = await res.json()
    
    if (res.status === 201) {
      successMessage.value = "Account created successfully! Please log in."
      isRegisterMode.value = false
      password.value = ""
    } else {
      errorMessage.value = data.error || "Registration failed"
    }
  } catch (error) {
    errorMessage.value = "Network error. Please try again."
  }
  
  isLoading.value = false
}

async function fetchUserInfo() {
  if (!token.value) return
  
  try {
    const res = await fetch("/api/user-info", {
      headers: { 
        "Authorization": `Bearer ${token.value}`
      }
    })
    
    if (res.ok) {
      const data = await res.json()
      userCreatedAt.value = data.created_at
    }
  } catch (error) {
    console.log("Could not fetch user info")
  }
}

async function logout() {
  isLoading.value = true
  
  try {
    await fetch("/api/logout", {
      method: "POST",
      headers: { 
        "Authorization": `Bearer ${token.value}`
      }
    })
  } catch (error) {
    console.log("Logout request failed, but continuing...")
  }
  
  // Clear local state
  token.value = ""
  currentUsername.value = ""
  videoUrl.value = ""
  userCreatedAt.value = ""
  username.value = ""
  password.value = ""
  
  // Clear localStorage
  localStorage.removeItem('authToken')
  localStorage.removeItem('currentUsername')
  
  isLoading.value = false
}

async function deleteAccount() {
  isLoading.value = true
  
  try {
    const res = await fetch("/api/delete-account", {
      method: "DELETE",
      headers: { 
        "Authorization": `Bearer ${token.value}`
      }
    })
    
    if (res.ok) {
      showDeleteConfirm.value = false
      successMessage.value = "Account deleted successfully"
      await logout()
    } else {
      const data = await res.json()
      errorMessage.value = data.error || "Failed to delete account"
    }
  } catch (error) {
    errorMessage.value = "Network error. Please try again."
  }
  
  isLoading.value = false
  showDeleteConfirm.value = false
}

function formatDate(dateString) {
  try {
    return new Date(dateString).toLocaleDateString()
  } catch {
    return dateString
  }
}
</script>

<style>
/* Force global styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
</style>

<style scoped>
#app {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
}

.container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #f8f9fa;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  overflow: hidden;
}

.background-video {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: -2;
}

.video-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  z-index: -1;
}

.title {
  font-size: 2.5rem;
  color: #ffffff;
  margin: 20px 0;
  font-weight: 300;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
  z-index: 1;
}

.auth-form {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  width: 400px;
  max-width: 90vw;
  z-index: 1;
}

.form-toggle {
  display: flex;
  margin-bottom: 25px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
}

.toggle-btn {
  flex: 1;
  padding: 12px;
  background: #f8f9fa;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.toggle-btn.active {
  background: #4a90e2;
  color: white;
}

.toggle-btn:hover:not(.active) {
  background: #e9ecef;
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.input-field {
  padding: 14px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
  background: rgba(255, 255, 255, 0.9);
}

.input-field:focus {
  border-color: #4a90e2;
  outline: none;
  background: rgba(255, 255, 255, 1);
}

.input-field.error {
  border-color: #e74c3c;
}

.error-message {
  color: #e74c3c;
  font-size: 0.9rem;
  text-align: left;
}

.success-message {
  color: #27ae60;
  font-size: 0.9rem;
  text-align: left;
}

.auth-btn {
  padding: 14px 20px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.auth-btn:hover:not(:disabled) {
  background-color: #357ab7;
}

.auth-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.stream-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #f8f9fa;
}

.user-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.username-display {
  font-size: 1.2rem;
  font-weight: 600;
  color: #2c3e50;
}

.user-since {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-top: 4px;
}

.user-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.change-password-btn {
  background-color: #f39c12;
  color: white;
}

.change-password-btn:hover {
  background-color: #e67e22;
}

.logout-btn {
  background-color: #95a5a6;
  color: white;
}

.logout-btn:hover {
  background-color: #7f8c8d;
}

.delete-btn {
  background-color: #e74c3c;
  color: white;
}

.delete-btn:hover {
  background-color: #c0392b;
}

.stream-title {
  font-size: 1.8rem;
  margin: 20px 0;
  color: #2c3e50;
}

.video-stream {
  max-width: 90%;
  max-height: calc(100vh - 200px);
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #ddd;
  margin: 0 auto;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-width: 400px;
  width: 90%;
  text-align: center;
}

.modal h3 {
  margin-bottom: 20px;
  font-size: 1.5rem;
  color: #2c3e50;
}

.modal p {
  color: #2c3e50;
  margin-bottom: 25px;
  line-height: 1.5;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 25px;
}

.modal-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.cancel-btn {
  padding: 10px 20px;
  background-color: #95a5a6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.cancel-btn:hover {
  background-color: #7f8c8d;
}

.confirm-btn {
  padding: 10px 20px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.confirm-btn:hover:not(:disabled) {
  background-color: #357ab7;
}

.confirm-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.delete-confirm-btn {
  padding: 10px 20px;
  background-color: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.delete-confirm-btn:hover:not(:disabled) {
  background-color: #c0392b;
}

.delete-confirm-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}
</style>