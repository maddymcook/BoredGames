import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { apiRequest } from "../api/client";

export const sendMessage = createAsyncThunk("messages/sendMessage", async (payload, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;

  if (!token || !userId) {
    throw new Error("Please log in before messaging.");
  }

  const message = await apiRequest("/messages/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      sender: userId,
      recipient: payload.recipient,
      listing: payload.listing,
      content: payload.content,
    }),
  });

  return message;
});

const messagesSlice = createSlice({
  name: "messages",
  initialState: {
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
      .addCase(sendMessage.pending, (state) => {
        state.sendStatus = "loading";
        state.sendError = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.sendStatus = "succeeded";
        state.lastMessage = action.payload;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.sendStatus = "failed";
        state.sendError = action.error.message || "Could not send message.";
      });
  },
});

export const { clearMessageState } = messagesSlice.actions;
export const selectMessages = (state) => state.messages;
export default messagesSlice.reducer;
