import { configureStore } from "@reduxjs/toolkit";

import authReducer from "./authSlice";
import listingsReducer from "./listingsSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    listings: listingsReducer,
  },
});
