import React, { useEffect } from "react";
import { Provider, useDispatch, useSelector } from "react-redux";
import {
  ActivityIndicator,
  Button,
  FlatList,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";

import { loginUser, registerAndLogin, selectAuth, setCredentialsForm } from "./src/store/authSlice";
import { createListing, fetchListings, selectListings, setDraftField } from "./src/store/listingsSlice";
import { store } from "./src/store/store";

function ListingsScreen() {
  const dispatch = useDispatch();
  const auth = useSelector(selectAuth);
  const listings = useSelector(selectListings);

  useEffect(() => {
    dispatch(fetchListings());
  }, [dispatch]);

  const submitAuth = async (isRegister) => {
    if (isRegister) {
      dispatch(registerAndLogin());
      return;
    }
    dispatch(loginUser());
  };

  const submitListing = async () => {
    await dispatch(createListing());
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.heading}>BoredGames Marketplace</Text>
      <Text style={styles.subheading}>Expo + Redux Toolkit + Django REST API</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Account</Text>
        {!auth.token ? (
          <>
            <TextInput
              style={styles.input}
              placeholder="Email"
              value={auth.form.email}
              autoCapitalize="none"
              onChangeText={(value) => dispatch(setCredentialsForm({ field: "email", value }))}
            />
            <TextInput
              style={styles.input}
              placeholder="Username (only for register)"
              value={auth.form.username}
              autoCapitalize="none"
              onChangeText={(value) => dispatch(setCredentialsForm({ field: "username", value }))}
            />
            <TextInput
              style={styles.input}
              placeholder="Password"
              secureTextEntry
              value={auth.form.password}
              onChangeText={(value) => dispatch(setCredentialsForm({ field: "password", value }))}
            />
            <View style={styles.row}>
              <Button title="Login" onPress={() => submitAuth(false)} />
              <Button title="Register + Login" onPress={() => submitAuth(true)} />
            </View>
          </>
        ) : (
          <Text style={styles.success}>Signed in as user #{auth.userId}</Text>
        )}
        {auth.error ? <Text style={styles.error}>{auth.error}</Text> : null}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Create Listing</Text>
        <TextInput
          style={styles.input}
          placeholder="Title"
          value={listings.draft.title}
          onChangeText={(value) => dispatch(setDraftField({ field: "title", value }))}
        />
        <TextInput
          style={styles.input}
          placeholder="Description"
          value={listings.draft.description}
          onChangeText={(value) => dispatch(setDraftField({ field: "description", value }))}
        />
        <TextInput
          style={styles.input}
          placeholder="Type (buy or swap)"
          value={listings.draft.listing_type}
          onChangeText={(value) => dispatch(setDraftField({ field: "listing_type", value }))}
        />
        <TextInput
          style={styles.input}
          placeholder="Price (required for buy)"
          value={listings.draft.price}
          keyboardType="decimal-pad"
          onChangeText={(value) => dispatch(setDraftField({ field: "price", value }))}
        />
        <TextInput
          style={styles.input}
          placeholder="ISO text (required for swap)"
          value={listings.draft.iso_text}
          onChangeText={(value) => dispatch(setDraftField({ field: "iso_text", value }))}
        />
        <Button title="Submit Listing" onPress={submitListing} />
        {listings.createError ? <Text style={styles.error}>{listings.createError}</Text> : null}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Listings</Text>
        {listings.status === "loading" ? (
          <ActivityIndicator />
        ) : (
          <FlatList
            data={listings.items}
            keyExtractor={(item) => String(item.id)}
            renderItem={({ item }) => (
              <View style={styles.listItem}>
                <Text style={styles.listTitle}>{item.title}</Text>
                <Text>{item.description || "No description"}</Text>
                <Text>Type: {item.listing_type}</Text>
                {item.price !== null ? <Text>Price: ${item.price}</Text> : null}
              </View>
            )}
          />
        )}
      </View>

      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <ListingsScreen />
    </Provider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 10,
  },
  heading: {
    fontSize: 24,
    fontWeight: "700",
  },
  subheading: {
    fontSize: 14,
    color: "#444",
  },
  card: {
    backgroundColor: "white",
    borderRadius: 8,
    padding: 12,
    gap: 8,
  },
  cardTitle: {
    fontWeight: "700",
    fontSize: 16,
  },
  input: {
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 8,
    backgroundColor: "#fff",
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  listItem: {
    borderBottomWidth: 1,
    borderBottomColor: "#eee",
    paddingVertical: 8,
  },
  listTitle: {
    fontSize: 15,
    fontWeight: "600",
  },
  success: {
    color: "#0b7a2f",
  },
  error: {
    color: "#a11",
  },
});
