import { configureStore } from "@reduxjs/toolkit";

import authReducer from "./authSlice";
import listingsReducer from "./listingsSlice";
import messagesReducer from "./messagesSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    listings: listingsReducer,
    messages: messagesReducer,
  },
});
