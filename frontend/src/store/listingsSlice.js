import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { Platform } from "react-native";

import { apiRequest } from "../api/client";

export const fetchListings = createAsyncThunk("listings/fetchListings", async () => {
  const data = await apiRequest("/listings/");
  return data.results || data;
});

export const fetchUsers = createAsyncThunk("listings/fetchUsers", async () => {
  const data = await apiRequest("/users/");
  return data.results || data;
});

export const fetchMyListings = createAsyncThunk("listings/fetchMyListings", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;
  if (!token || !userId) {
    throw new Error("Please log in to view your listings.");
  }
  const data = await apiRequest(`/listings/?owner=${userId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return data.results || data;
});

export const deleteListing = createAsyncThunk("listings/deleteListing", async (listingId, thunkApi) => {
  const state = thunkApi.getState();
  const { token } = state.auth;
  if (!token) {
    throw new Error("Please log in to delete a listing.");
  }
  await apiRequest(`/listings/${listingId}/`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return listingId;
});

export const createListing = createAsyncThunk("listings/createListing", async (_, thunkApi) => {
  const state = thunkApi.getState();
  const { token, userId } = state.auth;
  const draft = state.listings.draft;

  if (!token || !userId) {
    throw new Error("Please log in before creating a listing.");
  }

  const payload = {
    owner: String(userId),
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

  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      formData.append(key, String(value));
    }
  });
  if (draft.image) {
    if (Platform.OS === "web") {
      if (draft.image.file) {
        formData.append("image", draft.image.file, draft.image.fileName || draft.image.file?.name || "listing-image.jpg");
      } else if (draft.image.uri) {
        // Expo web can return an asset without a File object. Convert URI -> Blob.
        const response = await fetch(draft.image.uri);
        const blob = await response.blob();
        const inferredType = blob.type || draft.image.mimeType || "image/jpeg";
        const extension = inferredType.split("/")[1] || "jpg";
        const filename = draft.image.fileName || `listing-image.${extension}`;
        const fileBlob = blob.slice(0, blob.size, inferredType);
        formData.append("image", fileBlob, filename);
      } else {
        throw new Error("Please choose a valid image file.");
      }
    } else {
      formData.append("image", {
        uri: draft.image.uri,
        name: draft.image.fileName || "listing-image.jpg",
        type: draft.image.mimeType || "image/jpeg",
      });
    }
  }

  const tagNames = draft.tags
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  tagNames.forEach((tag) => formData.append("tag_names", tag));

  const created = await apiRequest("/listings/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
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
    myItems: [],
    myStatus: "idle",
    myError: null,
    deleteStatus: "idle",
    deleteError: null,
    createError: null,
    draft: {
      title: "",
      description: "",
      mode: "selling",
      price: "",
      iso_text: "",
      image: null,
      tags: "",
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
      .addCase(fetchMyListings.pending, (state) => {
        state.myStatus = "loading";
        state.myError = null;
      })
      .addCase(fetchMyListings.fulfilled, (state, action) => {
        state.myStatus = "succeeded";
        state.myItems = action.payload;
      })
      .addCase(fetchMyListings.rejected, (state, action) => {
        state.myStatus = "failed";
        state.myError = action.error.message || "Failed to load your listings.";
      })
      .addCase(createListing.pending, (state) => {
        state.createError = null;
      })
      .addCase(createListing.fulfilled, (state, action) => {
        state.items = [action.payload, ...state.items];
        state.myItems = [action.payload, ...state.myItems];
        state.draft.title = "";
        state.draft.description = "";
        state.draft.price = "";
        state.draft.iso_text = "";
        state.draft.image = null;
        state.draft.tags = "";
        state.draft.mode = "selling";
      })
      .addCase(createListing.rejected, (state, action) => {
        state.createError = action.error.message || "Failed to create listing";
      })
      .addCase(deleteListing.pending, (state) => {
        state.deleteStatus = "loading";
        state.deleteError = null;
      })
      .addCase(deleteListing.fulfilled, (state, action) => {
        state.deleteStatus = "succeeded";
        state.items = state.items.filter((item) => item.id !== action.payload);
        state.myItems = state.myItems.filter((item) => item.id !== action.payload);
      })
      .addCase(deleteListing.rejected, (state, action) => {
        state.deleteStatus = "failed";
        state.deleteError = action.error.message || "Failed to delete listing.";
      });
  },
});

export const { setDraftField } = listingsSlice.actions;
export const selectListings = (state) => state.listings;
export default listingsSlice.reducer;
