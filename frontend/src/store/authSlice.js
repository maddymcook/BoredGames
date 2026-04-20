import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { jwtDecode } from "jwt-decode";

import { apiRequest } from "../api/client";

function decodeUserIdFromToken(token) {
  try {
    const parsed = jwtDecode(token);
    return parsed.user_id || null;
  } catch (error) {
    return null;
  }
}

export const loginUser = createAsyncThunk("auth/loginUser", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { email, password } = state.auth.form;

  const tokenData = await apiRequest("/auth/token/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  return {
    access: tokenData.access,
    refresh: tokenData.refresh,
    userId: decodeUserIdFromToken(tokenData.access),
  };
});

export const registerAndLogin = createAsyncThunk("auth/registerAndLogin", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { email, username, password } = state.auth.form;

  await apiRequest("/users/", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });

  const tokenData = await apiRequest("/auth/token/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  return {
    access: tokenData.access,
    refresh: tokenData.refresh,
    userId: decodeUserIdFromToken(tokenData.access),
  };
});

export const registerUser = createAsyncThunk("auth/registerUser", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { email, username, password } = state.auth.form;

  await apiRequest("/users/", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
});

export const fetchCurrentUser = createAsyncThunk("auth/fetchCurrentUser", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;
  if (!token || !userId) {
    return null;
  }
  const user = await apiRequest(`/users/${userId}/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return user;
});

export const fetchMyProfile = createAsyncThunk("auth/fetchMyProfile", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { token } = state.auth;
  if (!token) {
    return null;
  }
  const profile = await apiRequest("/profiles/me/", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return profile;
});

export const saveMyProfile = createAsyncThunk("auth/saveMyProfile", async (payload, thunkApi) => {
  const state = thunkApi.getState();
  const { token } = state.auth;
  if (!token) {
    throw new Error("Please log in before saving your profile.");
  }
  const profile = await apiRequest("/profiles/me/", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return profile;
});

const authSlice = createSlice({
  name: "auth",
  initialState: {
    token: null,
    refreshToken: null,
    userId: null,
    status: "idle",
    error: null,
    registerStatus: "idle",
    registerError: null,
    registerSuccess: false,
    profileName: null,
    profile: null,
    profileStatus: "idle",
    profileError: null,
    profileSavedAt: null,
    form: {
      email: "",
      username: "",
      password: "",
    },
  },
  reducers: {
    setCredentialsForm(state, action) {
      state.form[action.payload.field] = action.payload.value;
    },
    clearRegisterFeedback(state) {
      state.registerError = null;
      state.registerSuccess = false;
      state.registerStatus = "idle";
    },
    clearProfileFeedback(state) {
      state.profileError = null;
      state.profileStatus = "idle";
      state.profileSavedAt = null;
    },
    logout(state) {
      state.token = null;
      state.refreshToken = null;
      state.userId = null;
      state.profileName = null;
      state.profile = null;
      state.profileStatus = "idle";
      state.profileError = null;
      state.profileSavedAt = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.token = action.payload.access;
        state.refreshToken = action.payload.refresh;
        state.userId = action.payload.userId;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message || "Login failed";
      })
      .addCase(registerAndLogin.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(registerAndLogin.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.token = action.payload.access;
        state.refreshToken = action.payload.refresh;
        state.userId = action.payload.userId;
      })
      .addCase(registerAndLogin.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message || "Registration failed";
      })
      .addCase(registerUser.pending, (state) => {
        state.registerStatus = "loading";
        state.registerError = null;
        state.registerSuccess = false;
      })
      .addCase(registerUser.fulfilled, (state) => {
        state.registerStatus = "succeeded";
        state.registerSuccess = true;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.registerStatus = "failed";
        state.registerError = action.error.message || "Registration failed";
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.profileName = action.payload?.profile_display_name || null;
      })
      .addCase(fetchMyProfile.pending, (state) => {
        state.profileStatus = "loading";
        state.profileError = null;
      })
      .addCase(fetchMyProfile.fulfilled, (state, action) => {
        state.profileStatus = "succeeded";
        state.profile = action.payload;
        state.profileName = action.payload?.display_name || state.profileName;
      })
      .addCase(fetchMyProfile.rejected, (state, action) => {
        state.profileStatus = "failed";
        state.profileError = action.error.message || "Could not load profile.";
      })
      .addCase(saveMyProfile.pending, (state) => {
        state.profileStatus = "loading";
        state.profileError = null;
      })
      .addCase(saveMyProfile.fulfilled, (state, action) => {
        state.profileStatus = "succeeded";
        state.profile = action.payload;
        state.profileName = action.payload?.display_name || state.profileName;
        state.profileSavedAt = Date.now();
      })
      .addCase(saveMyProfile.rejected, (state, action) => {
        state.profileStatus = "failed";
        state.profileError = action.error.message || "Could not save profile.";
      });
  },
});

export const { clearProfileFeedback, clearRegisterFeedback, logout, setCredentialsForm } = authSlice.actions;
export const selectAuth = (state) => state.auth;
export default authSlice.reducer;
