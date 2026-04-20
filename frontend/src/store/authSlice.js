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

const authSlice = createSlice({
  name: "auth",
  initialState: {
    token: null,
    refreshToken: null,
    userId: null,
    status: "idle",
    error: null,
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
    logout(state) {
      state.token = null;
      state.refreshToken = null;
      state.userId = null;
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
      });
  },
});

export const { logout, setCredentialsForm } = authSlice.actions;
export const selectAuth = (state) => state.auth;
export default authSlice.reducer;
