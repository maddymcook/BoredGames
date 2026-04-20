import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { apiRequest } from "../api/client";

export const fetchListings = createAsyncThunk("listings/fetchListings", async () => {
  const data = await apiRequest("/listings/");
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
    listing_type: draft.listing_type,
  };

  if (draft.listing_type === "buy") {
    payload.price = draft.price ? Number(draft.price) : null;
  } else {
    payload.iso_text = draft.iso_text;
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
    createError: null,
    draft: {
      title: "",
      description: "",
      listing_type: "buy",
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
      .addCase(createListing.pending, (state) => {
        state.createError = null;
      })
      .addCase(createListing.fulfilled, (state, action) => {
        state.items = [action.payload, ...state.items];
        state.draft.title = "";
        state.draft.description = "";
        state.draft.price = "";
        state.draft.iso_text = "";
      })
      .addCase(createListing.rejected, (state, action) => {
        state.createError = action.error.message || "Failed to create listing";
      });
  },
});

export const { setDraftField } = listingsSlice.actions;
export const selectListings = (state) => state.listings;
export default listingsSlice.reducer;
