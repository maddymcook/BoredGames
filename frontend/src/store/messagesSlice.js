import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { apiRequest } from "../api/client";

export const fetchMessages = createAsyncThunk("messages/fetchMessages", async (options, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;

  if (!token || !userId) {
    throw new Error("Please log in before viewing messages.");
  }

  const markRead = options?.markRead ? "true" : "false";
  const data = await apiRequest(`/messages/?mark_read=${markRead}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return {
    items: data.results || data,
    userId,
  };
});

export const sendMessage = createAsyncThunk("messages/sendMessage", async (payload, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;

  if (!token || !userId) {
    throw new Error("Please log in before messaging.");
  }

  try {
    const message = await apiRequest("/messages/", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        sender: Number(userId),
        recipient: Number(payload.recipient),
        listing: payload.listing ? Number(payload.listing) : null,
        content: payload.content,
      }),
    });
    return message;
  } catch (error) {
    return thunkApi.rejectWithValue(error.message || "Could not send message.");
  }
});

const messagesSlice = createSlice({
  name: "messages",
  initialState: {
    items: [],
    unreadCount: 0,
    listStatus: "idle",
    listError: null,
    sendStatus: "idle",
    sendError: null,
    lastMessage: null,
  },
  reducers: {
    clearMessageState(state) {
      state.sendError = null;
      state.sendStatus = "idle";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMessages.pending, (state) => {
        state.listStatus = "loading";
        state.listError = null;
      })
      .addCase(fetchMessages.fulfilled, (state, action) => {
        state.listStatus = "succeeded";
        state.items = action.payload.items;
        state.unreadCount = action.payload.items.filter(
          (item) => Number(item.recipient) === Number(action.payload.userId) && !item.is_read
        ).length;
      })
      .addCase(fetchMessages.rejected, (state, action) => {
        state.listStatus = "failed";
        state.listError = action.error.message || "Could not load messages.";
      })
      .addCase(sendMessage.pending, (state) => {
        state.sendStatus = "loading";
        state.sendError = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.sendStatus = "succeeded";
        state.lastMessage = action.payload;
        state.items = [action.payload, ...state.items];
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.sendStatus = "failed";
        state.sendError = action.payload || action.error.message || "Could not send message.";
      });
  },
});

export const { clearMessageState } = messagesSlice.actions;
export const selectMessages = (state) => state.messages;
export default messagesSlice.reducer;
