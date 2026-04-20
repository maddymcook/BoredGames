import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { apiRequest } from "../api/client";

export const fetchListings = createAsyncThunk("listings/fetchListings", async () => {
  const data = await apiRequest("/listings/");
  return data.results || data;
});

export const fetchUsers = createAsyncThunk("listings/fetchUsers", async () => {
  const data = await apiRequest("/users/");
  return data.results || data;
});

export const createListing = createAsyncThunk("listings/createListing", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;
  const draft = state.listings.draft;

  if (!token || !userId) {
    throw new Error("Please log in before creating a listing.");
  }

  const payload = {
    owner: userId,
    title: draft.title,
    description: draft.description,
  };

  if (draft.mode === "selling") {
    payload.listing_type = "buy";
    payload.price = draft.price ? Number(draft.price) : null;
  } else if (draft.mode === "swapping") {
    payload.listing_type = "swap";
    payload.iso_text = draft.iso_text;
  } else {
    payload.listing_type = "swap";
    payload.iso_text = draft.iso_text || `ISO: ${draft.title}`;
  }

  const created = await apiRequest("/listings/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  return created;
});

const listingsSlice = createSlice({
  name: "listings",
  initialState: {
    status: "idle",
    items: [],
    error: null,
    usersById: {},
    userStatus: "idle",
    userError: null,
    createError: null,
    draft: {
      title: "",
      description: "",
      mode: "selling",
      price: "",
      iso_text: "",
    },
  },
  reducers: {
    setDraftField(state, action) {
      state.draft[action.payload.field] = action.payload.value;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchListings.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchListings.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.items = action.payload;
      })
      .addCase(fetchListings.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message || "Failed to load listings";
      })
      .addCase(fetchUsers.pending, (state) => {
        state.userStatus = "loading";
      })
      .addCase(fetchUsers.fulfilled, (state, action) => {
        state.userStatus = "succeeded";
        state.usersById = action.payload.reduce((acc, user) => {
          acc[user.id] = user;
          return acc;
        }, {});
      })
      .addCase(fetchUsers.rejected, (state, action) => {
        state.userStatus = "failed";
        state.userError = action.error.message || "Failed to load users";
      })
      .addCase(createListing.pending, (state) => {
        state.createError = null;
      })
      .addCase(createListing.fulfilled, (state, action) => {
        state.items = [action.payload, ...state.items];
        state.draft.title = "";
        state.draft.description = "";
        state.draft.price = "";
        state.draft.iso_text = "";
        state.draft.mode = "selling";
      })
      .addCase(createListing.rejected, (state, action) => {
        state.createError = action.error.message || "Failed to create listing";
      });
  },
});

export const { setDraftField } = listingsSlice.actions;
export const selectListings = (state) => state.listings;
export default listingsSlice.reducer;
