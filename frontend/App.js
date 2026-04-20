import React, { useEffect, useMemo, useState } from "react";
import { Provider, useDispatch, useSelector } from "react-redux";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  ScrollView,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";

import { clearRegisterFeedback, loginUser, registerUser, selectAuth, setCredentialsForm } from "./src/store/authSlice";
import { sendMessage, selectMessages } from "./src/store/messagesSlice";
import { createListing, fetchListings, fetchUsers, selectListings, setDraftField } from "./src/store/listingsSlice";
import { store } from "./src/store/store";

function AuthGate() {
  const dispatch = useDispatch();
  const auth = useSelector(selectAuth);

  const onLogin = () => dispatch(loginUser());
  const onRegister = () => dispatch(registerUser());

  return (
    <View style={styles.authContainer}>
      <Text style={styles.authHeading}>Welcome to BoredGames Marketplace</Text>
      <Text style={styles.authSubheading}>Create an account, then log in to open the app.</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        value={auth.form.email}
        onChangeText={(value) => dispatch(setCredentialsForm({ field: "email", value }))}
      />
      <TextInput
        style={styles.input}
        placeholder="Username (for account creation)"
        autoCapitalize="none"
        value={auth.form.username}
        onChangeText={(value) => {
          dispatch(clearRegisterFeedback());
          dispatch(setCredentialsForm({ field: "username", value }));
        }}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={auth.form.password}
        onChangeText={(value) => {
          dispatch(clearRegisterFeedback());
          dispatch(setCredentialsForm({ field: "password", value }));
        }}
      />

      <View style={styles.row}>
        <Pressable style={styles.secondaryButton} onPress={onRegister}>
          <Text style={styles.secondaryButtonText}>
            {auth.registerStatus === "loading" ? "Creating..." : "Create Account"}
          </Text>
        </Pressable>
        <Pressable style={styles.primaryButton} onPress={onLogin}>
          <Text style={styles.primaryButtonText}>{auth.status === "loading" ? "Logging in..." : "Login"}</Text>
        </Pressable>
      </View>

      {auth.registerSuccess ? <Text style={styles.success}>Account created. Now log in.</Text> : null}
      {auth.registerError ? <Text style={styles.error}>{auth.registerError}</Text> : null}
      {auth.error ? <Text style={styles.error}>{auth.error}</Text> : null}
    </View>
  );
}

function MarketplaceApp() {
  const dispatch = useDispatch();
  const auth = useSelector(selectAuth);
  const listings = useSelector(selectListings);
  const messages = useSelector(selectMessages);
  const [activeTab, setActiveTab] = useState("browse");
  const [profile, setProfile] = useState({ displayName: "", location: "", bio: "" });
  const [profileSaved, setProfileSaved] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [selectedListingId, setSelectedListingId] = useState(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [feedFilter, setFeedFilter] = useState("all");

  useEffect(() => {
    dispatch(fetchListings());
    dispatch(fetchUsers());
  }, [dispatch]);

  const listingModeLabels = { selling: "Selling", swapping: "Swapping", in_search_of: "In Search Of" };
  const listingTypeLabels = { buy: "Selling", swap: "Swap/ISO" };
  const selectedListing = useMemo(
    () => listings.items.find((item) => item.id === selectedListingId) || null,
    [listings.items, selectedListingId]
  );

  const filteredListings = useMemo(() => {
    return listings.items.filter((item) => {
      const matchesText =
        searchText.trim().length === 0 ||
        item.title.toLowerCase().includes(searchText.toLowerCase()) ||
        (item.description || "").toLowerCase().includes(searchText.toLowerCase()) ||
        (item.iso_text || "").toLowerCase().includes(searchText.toLowerCase());

      const mode = item.listing_type === "buy" ? "selling" : item.iso_text?.toLowerCase().startsWith("iso:") ? "in_search_of" : "swapping";
      const matchesFilter = feedFilter === "all" || feedFilter === mode;
      return matchesText && matchesFilter;
    });
  }, [listings.items, searchText, feedFilter]);

  const submitListing = async () => {
    const result = await dispatch(createListing());
    if (!result.error) {
      Alert.alert("Listing posted", "Your listing is now live in the marketplace.");
      setActiveTab("browse");
    }
  };

  const saveProfile = () => {
    setProfileSaved(true);
    Alert.alert("Profile saved", "Your local profile details were saved in this session.");
  };

  const onSendMessage = async () => {
    if (!selectedListing) {
      return;
    }
    if (!messageDraft.trim()) {
      Alert.alert("Message required", "Write a message before sending.");
      return;
    }
    if (!auth.userId || selectedListing.owner === auth.userId) {
      Alert.alert("Cannot send", "You cannot message your own listing.");
      return;
    }

    const result = await dispatch(
      sendMessage({
        recipient: selectedListing.owner,
        listing: selectedListing.id,
        content: messageDraft.trim(),
      })
    );
    if (!result.error) {
      setMessageDraft("");
      Alert.alert("Message sent", "The listing owner can now view your message.");
    }
  };

  const ownerName = (ownerId) => {
    const user = listings.usersById[ownerId];
    if (!user) {
      return `User #${ownerId}`;
    }
    return user.username || user.email || `User #${ownerId}`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <Text style={styles.brand}>BoredGames Marketplace</Text>
        <Text style={styles.topMeta}>Signed in as #{auth.userId}</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {activeTab === "browse" ? (
          <>
            <View style={styles.searchBar}>
              <TextInput
                style={styles.searchInput}
                placeholder="Search listings, game names, ISO notes..."
                value={searchText}
                onChangeText={setSearchText}
              />
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>All Listings</Text>
              <View style={styles.rowWrap}>
                {["all", "selling", "swapping", "in_search_of"].map((filter) => (
                  <Pressable
                    key={filter}
                    style={feedFilter === filter ? styles.modeButtonActive : styles.modeButton}
                    onPress={() => setFeedFilter(filter)}
                  >
                    <Text style={feedFilter === filter ? styles.modeTextActive : styles.modeText}>
                      {filter === "all" ? "All" : listingModeLabels[filter]}
                    </Text>
                  </Pressable>
                ))}
              </View>

              {listings.status === "loading" ? (
                <ActivityIndicator />
              ) : (
                <FlatList
                  data={filteredListings}
                  scrollEnabled={false}
                  keyExtractor={(item) => String(item.id)}
                  ListEmptyComponent={<Text style={styles.subtleText}>No listings match your search.</Text>}
                  renderItem={({ item }) => (
                    <Pressable style={styles.listingCard} onPress={() => setSelectedListingId(item.id)}>
                      <View style={styles.listingCardTop}>
                        <Text style={styles.listTitle}>{item.title}</Text>
                        <Text style={styles.tag}>{listingTypeLabels[item.listing_type] || item.listing_type}</Text>
                      </View>
                      <Text style={styles.subtleText}>Owner: {ownerName(item.owner)}</Text>
                      <Text>{item.description || "No description provided."}</Text>
                      {item.price !== null ? <Text style={styles.price}>${item.price}</Text> : null}
                      {item.iso_text ? <Text style={styles.subtleText}>{item.iso_text}</Text> : null}
                    </Pressable>
                  )}
                />
              )}
            </View>

            {selectedListing ? (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>Listing Details</Text>
                <Text style={styles.detailTitle}>{selectedListing.title}</Text>
                <Text style={styles.subtleText}>Posted by {ownerName(selectedListing.owner)}</Text>
                <Text>{selectedListing.description || "No description provided."}</Text>
                {selectedListing.price !== null ? <Text style={styles.price}>${selectedListing.price}</Text> : null}
                {selectedListing.iso_text ? <Text style={styles.subtleText}>{selectedListing.iso_text}</Text> : null}

                <Text style={styles.cardSubTitle}>Message Listing Owner</Text>
                <TextInput
                  style={[styles.input, styles.multilineInput]}
                  placeholder="Hi! Is this still available?"
                  multiline
                  value={messageDraft}
                  onChangeText={setMessageDraft}
                />
                <Pressable
                  style={
                    auth.token && auth.userId !== selectedListing.owner ? styles.primaryButton : styles.disabledButton
                  }
                  onPress={onSendMessage}
                  disabled={!auth.token || auth.userId === selectedListing.owner || messages.sendStatus === "loading"}
                >
                  <Text style={styles.primaryButtonText}>
                    {messages.sendStatus === "loading" ? "Sending..." : "Send Message"}
                  </Text>
                </Pressable>
                {messages.sendError ? <Text style={styles.error}>{messages.sendError}</Text> : null}
                {messages.sendStatus === "succeeded" ? (
                  <Text style={styles.success}>Message sent successfully.</Text>
                ) : null}
              </View>
            ) : null}
          </>
        ) : null}

        {activeTab === "sell" ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Add Listing</Text>
            <View style={styles.rowWrap}>
              {["selling", "swapping", "in_search_of"].map((mode) => (
                <Pressable
                  key={mode}
                  style={listings.draft.mode === mode ? styles.modeButtonActive : styles.modeButton}
                  onPress={() => dispatch(setDraftField({ field: "mode", value: mode }))}
                >
                  <Text style={listings.draft.mode === mode ? styles.modeTextActive : styles.modeText}>
                    {listingModeLabels[mode]}
                  </Text>
                </Pressable>
              ))}
            </View>
            <TextInput
              style={styles.input}
              placeholder="Listing title"
              value={listings.draft.title}
              onChangeText={(value) => dispatch(setDraftField({ field: "title", value }))}
            />
            <TextInput
              style={[styles.input, styles.multilineInput]}
              placeholder="Description"
              value={listings.draft.description}
              multiline
              onChangeText={(value) => dispatch(setDraftField({ field: "description", value }))}
            />
            {listings.draft.mode === "selling" ? (
              <TextInput
                style={styles.input}
                placeholder="Price (required)"
                value={listings.draft.price}
                keyboardType="decimal-pad"
                onChangeText={(value) => dispatch(setDraftField({ field: "price", value }))}
              />
            ) : (
              <TextInput
                style={styles.input}
                placeholder={listings.draft.mode === "in_search_of" ? "What are you looking for?" : "What are you offering/wanting?"}
                value={listings.draft.iso_text}
                onChangeText={(value) => dispatch(setDraftField({ field: "iso_text", value }))}
              />
            )}
            <Pressable style={styles.primaryButton} onPress={submitListing}>
              <Text style={styles.primaryButtonText}>Post Listing</Text>
            </Pressable>
            {listings.createError ? <Text style={styles.error}>{listings.createError}</Text> : null}
          </View>
        ) : null}

        {activeTab === "profile" ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Create Your Profile</Text>
            <TextInput
              style={styles.input}
              placeholder="Display name"
              value={profile.displayName}
              onChangeText={(value) => setProfile((prev) => ({ ...prev, displayName: value }))}
            />
            <TextInput
              style={styles.input}
              placeholder="Campus / location"
              value={profile.location}
              onChangeText={(value) => setProfile((prev) => ({ ...prev, location: value }))}
            />
            <TextInput
              style={[styles.input, styles.multilineInput]}
              placeholder="Bio / trade preferences"
              value={profile.bio}
              multiline
              onChangeText={(value) => setProfile((prev) => ({ ...prev, bio: value }))}
            />
            <Pressable style={styles.primaryButton} onPress={saveProfile}>
              <Text style={styles.primaryButtonText}>Save Profile</Text>
            </Pressable>
            {profileSaved ? <Text style={styles.success}>Profile section ready.</Text> : null}
          </View>
        ) : null}
      </ScrollView>

      <View style={styles.tabBar}>
        <Pressable style={activeTab === "browse" ? styles.tabActive : styles.tab} onPress={() => setActiveTab("browse")}>
          <Text style={activeTab === "browse" ? styles.tabTextActive : styles.tabText}>Browse</Text>
        </Pressable>
        <Pressable style={activeTab === "sell" ? styles.tabActive : styles.tab} onPress={() => setActiveTab("sell")}>
          <Text style={activeTab === "sell" ? styles.tabTextActive : styles.tabText}>Add Listing</Text>
        </Pressable>
        <Pressable style={activeTab === "profile" ? styles.tabActive : styles.tab} onPress={() => setActiveTab("profile")}>
          <Text style={activeTab === "profile" ? styles.tabTextActive : styles.tabText}>Profile</Text>
        </Pressable>
      </View>
    </View>
  );
}

function RootApp() {
  const auth = useSelector(selectAuth);

  return (
    <SafeAreaView style={styles.container}>
      {!auth.token ? <AuthGate /> : <MarketplaceApp />}
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <RootApp />
    </Provider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#eef2f7",
  },
  authContainer: {
    flex: 1,
    padding: 18,
    justifyContent: "center",
    gap: 10,
  },
  authHeading: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1f2a37",
  },
  authSubheading: {
    color: "#566070",
    marginBottom: 8,
  },
  topBar: {
    backgroundColor: "#1877f2",
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
  },
  brand: {
    color: "white",
    fontSize: 22,
    fontWeight: "700",
  },
  topMeta: {
    color: "#dbe8ff",
    marginTop: 2,
  },
  scrollContent: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 12,
  },
  searchBar: {
    backgroundColor: "white",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#d6deea",
  },
  searchInput: {
    fontSize: 15,
  },
  card: {
    backgroundColor: "white",
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: "#d6deea",
    gap: 8,
  },
  cardTitle: {
    fontWeight: "700",
    fontSize: 17,
    color: "#1f2a37",
  },
  cardSubTitle: {
    fontWeight: "600",
    fontSize: 15,
    marginTop: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: "#c8d1dc",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    backgroundColor: "#fff",
  },
  multilineInput: {
    minHeight: 70,
    textAlignVertical: "top",
  },
  row: {
    flexDirection: "row",
    gap: 10,
  },
  rowWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  primaryButton: {
    backgroundColor: "#1877f2",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: "center",
    flex: 1,
  },
  secondaryButton: {
    backgroundColor: "#e7f0ff",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: "center",
    flex: 1,
  },
  disabledButton: {
    backgroundColor: "#99afcf",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "white",
    fontWeight: "700",
  },
  secondaryButtonText: {
    color: "#0f4fa8",
    fontWeight: "700",
  },
  modeButton: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 99,
    borderWidth: 1,
    borderColor: "#c8d1dc",
    backgroundColor: "#f8fafc",
  },
  modeButtonActive: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 99,
    borderWidth: 1,
    borderColor: "#1877f2",
    backgroundColor: "#e9f2ff",
  },
  modeText: {
    color: "#334155",
    fontWeight: "500",
  },
  modeTextActive: {
    color: "#1256af",
    fontWeight: "700",
  },
  listingCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    gap: 4,
    backgroundColor: "#fbfdff",
  },
  listingCardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  listTitle: {
    fontSize: 15,
    fontWeight: "600",
  },
  tag: {
    fontSize: 12,
    color: "#1d4ed8",
    fontWeight: "700",
  },
  detailTitle: {
    fontSize: 18,
    fontWeight: "700",
  },
  price: {
    fontSize: 16,
    fontWeight: "700",
    color: "#14532d",
  },
  subtleText: {
    color: "#5b6470",
  },
  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: "#d6deea",
    backgroundColor: "white",
    paddingHorizontal: 8,
    paddingVertical: 8,
    gap: 8,
  },
  tab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "#edf2f7",
  },
  tabActive: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "#dbeafe",
  },
  tabText: {
    color: "#475569",
    fontWeight: "600",
  },
  tabTextActive: {
    color: "#1d4ed8",
    fontWeight: "700",
  },
  success: {
    color: "#0b7a2f",
  },
  error: {
    color: "#a11",
  },
});
