import React, { useEffect, useMemo, useState } from "react";
import { Provider, useDispatch, useSelector } from "react-redux";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  Pressable,
  ScrollView,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import * as ImagePicker from "expo-image-picker";

import {
  clearProfileFeedback,
  clearRegisterFeedback,
  fetchCurrentUser,
  fetchMyProfile,
  loginUser,
  registerUser,
  saveMyProfile,
  selectAuth,
  setCredentialsForm,
} from "./src/store/authSlice";
import { fetchMessages, sendMessage, selectMessages } from "./src/store/messagesSlice";
import {
  createListing,
  deleteListing,
  fetchListings,
  fetchMyListings,
  fetchUsers,
  selectListings,
  setDraftField,
} from "./src/store/listingsSlice";
import { toAbsoluteMediaUrl } from "./src/api/client";
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
  const [activeTab, setActiveTab] = useState("listings");
  const [profile, setProfile] = useState({ displayName: "", location: "", bio: "" });
  const [profileSaved, setProfileSaved] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [selectedListingId, setSelectedListingId] = useState(null);
  const [selectedThreadKey, setSelectedThreadKey] = useState(null);
  const [selectedRecipientId, setSelectedRecipientId] = useState(null);
  const [selectedRecipientName, setSelectedRecipientName] = useState("");
  const [selectedListingContextId, setSelectedListingContextId] = useState(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [feedFilter, setFeedFilter] = useState("all");

  useEffect(() => {
    dispatch(fetchListings());
    dispatch(fetchUsers());
    dispatch(fetchMessages({ markRead: false }));
  }, [dispatch]);

  useEffect(() => {
    if (auth.token && auth.userId) {
      dispatch(fetchCurrentUser());
      dispatch(fetchMyProfile());
      dispatch(fetchMyListings());
    }
  }, [dispatch, auth.token, auth.userId]);

  useEffect(() => {
    if (auth.profile) {
      setProfile({
        displayName: auth.profile.display_name || "",
        location: auth.profile.looking_for || "",
        bio: auth.profile.credentials || "",
      });
    }
  }, [auth.profile]);

  useEffect(() => {
    if (!auth.token) {
      return undefined;
    }
    const timer = setInterval(() => {
      dispatch(fetchMessages({ markRead: activeTab === "messages" }));
    }, 5000);
    return () => clearInterval(timer);
  }, [dispatch, auth.token, activeTab]);

  useEffect(() => {
    if (activeTab === "messages" && auth.token) {
      dispatch(fetchMessages({ markRead: true }));
    }
  }, [dispatch, activeTab, auth.token]);

  const listingModeLabels = { selling: "Selling", swapping: "Swapping", in_search_of: "In Search Of" };
  const listingTypeLabels = { buy: "Selling", swap: "Swap/ISO" };
  const selectedListing = useMemo(
    () => listings.items.find((item) => item.id === selectedListingId) || null,
    [listings.items, selectedListingId]
  );
  const messageThreads = useMemo(() => {
    if (!auth.userId) {
      return [];
    }
    const threadMap = new Map();
    messages.items.forEach((message) => {
      const otherUserId =
        Number(message.sender) === Number(auth.userId) ? message.recipient : message.sender;
      if (Number(otherUserId) === Number(auth.userId)) {
        return;
      }
      const key = `${otherUserId}`;
      const existing = threadMap.get(key);
      const unread = Number(message.recipient) === Number(auth.userId) && !message.is_read ? 1 : 0;
      if (!existing) {
        threadMap.set(key, {
          key,
          otherUserId,
          latestMessage: message,
          unreadCount: unread,
        });
        return;
      }
      if (new Date(message.created_at) > new Date(existing.latestMessage.created_at)) {
        existing.latestMessage = message;
      }
      existing.unreadCount += unread;
    });
    return Array.from(threadMap.values()).sort(
      (a, b) => new Date(b.latestMessage.created_at) - new Date(a.latestMessage.created_at)
    );
  }, [messages.items, auth.userId]);

  useEffect(() => {
    if (!selectedThreadKey && messageThreads.length > 0) {
      const first = messageThreads[0];
      setSelectedThreadKey(first.key);
      setSelectedRecipientId(first.otherUserId);
      setSelectedRecipientName(ownerName(first.otherUserId));
      setSelectedListingContextId(first.latestMessage?.listing || null);
    }
  }, [selectedThreadKey, messageThreads]);

  const selectedThread = useMemo(
    () => messageThreads.find((thread) => thread.key === selectedThreadKey) || null,
    [messageThreads, selectedThreadKey]
  );

  const threadMessages = useMemo(() => {
    if (!selectedThread || !auth.userId) {
      return [];
    }
    return messages.items
      .filter((item) => {
        const otherUserId =
          Number(item.sender) === Number(auth.userId) ? item.recipient : item.sender;
        return Number(otherUserId) === Number(selectedThread.otherUserId);
      })
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  }, [messages.items, selectedThread, auth.userId]);

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

  const pickListingImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Permission required", "Allow photo access to upload listing images.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsMultipleSelection: false,
    });
    if (!result.canceled && result.assets?.length) {
      dispatch(setDraftField({ field: "image", value: result.assets[0] }));
    }
  };

  const submitListing = async () => {
    const result = await dispatch(createListing());
    if (!result.error) {
      Alert.alert("Listing posted", "Your listing is now live in the marketplace.");
      setActiveTab("listings");
      dispatch(fetchListings());
    }
  };

  const saveProfile = async () => {
    dispatch(clearProfileFeedback());
    const result = await dispatch(
      saveMyProfile({
        display_name: profile.displayName,
        credentials: profile.bio,
        looking_for: profile.location,
      })
    );
    if (!result.error) {
      setProfileSaved(true);
      dispatch(fetchUsers());
      dispatch(fetchCurrentUser());
      Alert.alert("Profile saved", "Your profile name is now used across listings.");
    }
  };

  const onSendMessage = async () => {
    const recipientId = selectedRecipientId;
    const listingId = selectedListingContextId;
    if (!recipientId) {
      Alert.alert("Select a conversation", "Choose a thread or click a listing first.");
      return;
    }
    if (!messageDraft.trim()) {
      Alert.alert("Message required", "Write a message before sending.");
      return;
    }
    if (!auth.userId || Number(recipientId) === Number(auth.userId)) {
      Alert.alert("Cannot send", "You cannot message your own listing.");
      return;
    }

    try {
      await dispatch(
        sendMessage({
          recipient: recipientId,
          listing: listingId,
          content: messageDraft.trim(),
        })
      ).unwrap();
      setMessageDraft("");
      if (!selectedThreadKey && selectedRecipientId) {
        setSelectedThreadKey(String(selectedRecipientId));
      }
      dispatch(fetchMessages({ markRead: activeTab === "messages" }));
      Alert.alert("Message sent", "The listing owner can now view your message.");
    } catch (error) {
      Alert.alert("Could not send message", error?.message || "Please try again.");
    }
  };

  const onDeleteListing = async (listingId) => {
    const result = await dispatch(deleteListing(listingId));
    if (!result.error) {
      Alert.alert("Listing deleted", "Your listing has been removed.");
      dispatch(fetchListings());
      dispatch(fetchMyListings());
      return;
    }
    Alert.alert("Delete failed", result.error.message || "Could not delete listing.");
  };

  const ownerName = (ownerId) => {
    const user = listings.usersById[ownerId];
    if (!user) {
      return `User #${ownerId}`;
    }
    return user.profile_display_name || user.username || user.email || `User #${ownerId}`;
  };

  const listingOwnerName = (listing) => listing?.owner_display_name || ownerName(listing?.owner);
  const listingTitleById = (listingId) => {
    if (!listingId) {
      return "General chat";
    }
    const listing = listings.items.find((item) => Number(item.id) === Number(listingId));
    return listing?.title || `Listing #${listingId}`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <Text style={styles.brand}>BoredGames Marketplace</Text>
        <Text style={styles.topMeta}>Signed in as {auth.profileName || ownerName(auth.userId)}</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {activeTab === "listings" ? (
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
                    <Pressable
                      style={styles.listingCard}
                      onPress={() => {
                        if (Number(item.owner) === Number(auth.userId)) {
                          Alert.alert("Your listing", "This is your own listing, so messaging is disabled.");
                          return;
                        }
                        setSelectedListingId(item.id);
                        setSelectedThreadKey(String(item.owner));
                        setSelectedRecipientId(item.owner);
                        setSelectedRecipientName(listingOwnerName(item));
                        setSelectedListingContextId(item.id);
                        setActiveTab("messages");
                      }}
                    >
                      {item.image ? (
                        <Image source={{ uri: toAbsoluteMediaUrl(item.image) }} style={styles.listingImage} />
                      ) : null}
                      <View style={styles.listingCardTop}>
                        <Text style={styles.listTitle}>{item.title}</Text>
                        <Text style={styles.tag}>{listingTypeLabels[item.listing_type] || item.listing_type}</Text>
                      </View>
                      <Text style={styles.subtleText}>Owner: {listingOwnerName(item)}</Text>
                      <Text>{item.description || "No description provided."}</Text>
                      {item.price !== null ? <Text style={styles.price}>${item.price}</Text> : null}
                      {item.iso_text ? <Text style={styles.subtleText}>{item.iso_text}</Text> : null}
                      {item.tags?.length ? <Text style={styles.subtleText}>Tags: {item.tags.join(", ")}</Text> : null}
                    </Pressable>
                  )}
                />
              )}
            </View>

            {selectedListing ? (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>Listing Details</Text>
                <Text style={styles.detailTitle}>{selectedListing.title}</Text>
                <Text style={styles.subtleText}>Posted by {listingOwnerName(selectedListing)}</Text>
                <Text>{selectedListing.description || "No description provided."}</Text>
                {selectedListing.price !== null ? <Text style={styles.price}>${selectedListing.price}</Text> : null}
                {selectedListing.iso_text ? <Text style={styles.subtleText}>{selectedListing.iso_text}</Text> : null}
                {selectedListing.tags?.length ? (
                  <Text style={styles.subtleText}>Tags: {selectedListing.tags.join(", ")}</Text>
                ) : null}

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

        {activeTab === "messages" ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Messaging</Text>
            <FlatList
              data={messageThreads}
              scrollEnabled={false}
              keyExtractor={(item) => item.key}
              ListEmptyComponent={<Text style={styles.subtleText}>No conversations yet.</Text>}
              renderItem={({ item }) => (
                <Pressable
                  style={selectedThread?.key === item.key ? styles.threadCardActive : styles.threadCard}
                  onPress={() => {
                    setSelectedThreadKey(item.key);
                    setSelectedRecipientId(item.otherUserId);
                    setSelectedRecipientName(ownerName(item.otherUserId));
                    setSelectedListingContextId(item.latestMessage?.listing || null);
                  }}
                >
                  <View style={styles.threadRow}>
                    <Text style={styles.listTitle}>{ownerName(item.otherUserId)}</Text>
                    {item.unreadCount > 0 ? (
                      <View style={styles.badge}>
                        <Text style={styles.badgeText}>{item.unreadCount > 99 ? "99+" : item.unreadCount}</Text>
                      </View>
                    ) : null}
                  </View>
                  <Text style={styles.subtleText} numberOfLines={1}>
                    {listingTitleById(item.latestMessage?.listing)}
                  </Text>
                </Pressable>
              )}
            />
            {selectedThread ? (
              <FlatList
                data={threadMessages}
                scrollEnabled={false}
                keyExtractor={(item) => `msg-${item.id}`}
                ListEmptyComponent={<Text style={styles.subtleText}>No messages yet. Start the conversation.</Text>}
                renderItem={({ item }) => (
                  <View
                    style={
                      Number(item.sender) === Number(auth.userId) ? styles.messageBubbleMine : styles.messageBubbleTheirs
                    }
                  >
                    <Text style={styles.messageText}>{item.content}</Text>
                  </View>
                )}
              />
            ) : null}
            {selectedThread || selectedListing ? (
              <View style={styles.messageComposeCard}>
                <Text style={styles.cardSubTitle}>
                  Message {selectedRecipientName || (selectedThread ? ownerName(selectedThread.otherUserId) : listingOwnerName(selectedListing))}
                </Text>
                <TextInput
                  style={[styles.input, styles.multilineInput]}
                  placeholder="Write your message..."
                  multiline
                  value={messageDraft}
                  onChangeText={setMessageDraft}
                />
                <Pressable
                  style={
                    auth.token &&
                    selectedRecipientId &&
                    Number(auth.userId) !== Number(selectedRecipientId)
                      ? styles.primaryButton
                      : styles.disabledButton
                  }
                  onPress={onSendMessage}
                  disabled={
                    !auth.token ||
                    !selectedRecipientId ||
                    Number(auth.userId) === Number(selectedRecipientId) ||
                    messages.sendStatus === "loading"
                  }
                >
                  <Text style={styles.primaryButtonText}>
                    {messages.sendStatus === "loading" ? "Sending..." : "Send Message"}
                  </Text>
                </Pressable>
                {messages.sendError ? <Text style={styles.error}>{messages.sendError}</Text> : null}
              </View>
            ) : (
              <Text style={styles.subtleText}>Choose a conversation or click a listing to start one.</Text>
            )}
            {messages.listStatus === "loading" ? (
              <ActivityIndicator />
            ) : (
              <></>
            )}
            {messages.listError ? <Text style={styles.error}>{messages.listError}</Text> : null}
          </View>
        ) : null}

        {activeTab === "profile" ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Profile</Text>
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
              <Text style={styles.primaryButtonText}>
                {auth.profileStatus === "loading" ? "Saving..." : "Save Profile"}
              </Text>
            </Pressable>
            {profileSaved ? <Text style={styles.success}>Profile section ready.</Text> : null}
            {auth.profileSavedAt ? <Text style={styles.success}>Profile saved.</Text> : null}
            {auth.profileError ? <Text style={styles.error}>{auth.profileError}</Text> : null}
          </View>
        ) : null}

        {activeTab === "profile" ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>My Listings</Text>
            {listings.myStatus === "loading" ? (
              <ActivityIndicator />
            ) : (
              <FlatList
                data={listings.myItems}
                scrollEnabled={false}
                keyExtractor={(item) => `my-${item.id}`}
                ListEmptyComponent={<Text style={styles.subtleText}>You have no listings yet.</Text>}
                renderItem={({ item }) => (
                  <View style={styles.myListingCard}>
                    <Text style={styles.listTitle}>{item.title}</Text>
                    <Text style={styles.subtleText}>
                      {item.listing_type === "buy" ? "Selling" : "Swap/ISO"} {item.price !== null ? `- $${item.price}` : ""}
                    </Text>
                    <Text numberOfLines={2}>{item.description || "No description"}</Text>
                    <Pressable
                      style={styles.deleteButton}
                      onPress={() => onDeleteListing(item.id)}
                      disabled={listings.deleteStatus === "loading"}
                    >
                      <Text style={styles.deleteButtonText}>
                        {listings.deleteStatus === "loading" ? "Deleting..." : "Delete Listing"}
                      </Text>
                    </Pressable>
                  </View>
                )}
              />
            )}
            {listings.myError ? <Text style={styles.error}>{listings.myError}</Text> : null}
            {listings.deleteError ? <Text style={styles.error}>{listings.deleteError}</Text> : null}
          </View>
        ) : null}

        {activeTab === "profile" ? (
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
            <TextInput
              style={styles.input}
              placeholder="Tags (comma-separated, e.g. card games, fantasy, deck building)"
              value={listings.draft.tags}
              onChangeText={(value) => dispatch(setDraftField({ field: "tags", value }))}
            />
            {listings.draft.image ? (
              <Image source={{ uri: listings.draft.image.uri }} style={styles.previewImage} />
            ) : (
              <Text style={styles.subtleText}>No image selected</Text>
            )}
            <Pressable style={styles.secondaryButton} onPress={pickListingImage}>
              <Text style={styles.secondaryButtonText}>Upload Listing Image</Text>
            </Pressable>
            <Pressable style={styles.primaryButton} onPress={submitListing}>
              <Text style={styles.primaryButtonText}>Post Listing</Text>
            </Pressable>
            {listings.createError ? <Text style={styles.error}>{listings.createError}</Text> : null}
          </View>
        ) : null}
      </ScrollView>

      <View style={styles.tabBar}>
        <Pressable style={activeTab === "listings" ? styles.tabActive : styles.tab} onPress={() => setActiveTab("listings")}>
          <Text style={activeTab === "listings" ? styles.tabTextActive : styles.tabText}>All Listings</Text>
        </Pressable>
        <Pressable style={activeTab === "messages" ? styles.tabActive : styles.tab} onPress={() => setActiveTab("messages")}>
          <View style={styles.tabLabelRow}>
            <Text style={activeTab === "messages" ? styles.tabTextActive : styles.tabText}>Messaging</Text>
            {messages.unreadCount > 0 ? (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{messages.unreadCount > 99 ? "99+" : messages.unreadCount}</Text>
              </View>
            ) : null}
          </View>
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
  listingImage: {
    width: "100%",
    height: 170,
    borderRadius: 8,
    marginBottom: 6,
    backgroundColor: "#dbe6f7",
  },
  previewImage: {
    width: "100%",
    height: 200,
    borderRadius: 8,
    backgroundColor: "#dbe6f7",
  },
  messageCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    gap: 3,
    backgroundColor: "#fbfdff",
  },
  messageBubbleMine: {
    alignSelf: "flex-end",
    backgroundColor: "#dbeafe",
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 6,
    maxWidth: "84%",
  },
  messageBubbleTheirs: {
    alignSelf: "flex-start",
    backgroundColor: "#f1f5f9",
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 6,
    maxWidth: "84%",
  },
  messageText: {
    color: "#0f172a",
  },
  messageComposeCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 10,
    padding: 10,
    gap: 6,
    backgroundColor: "#fbfdff",
    marginBottom: 10,
  },
  myListingCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    gap: 4,
    backgroundColor: "#fbfdff",
  },
  deleteButton: {
    marginTop: 6,
    backgroundColor: "#fee2e2",
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: "center",
  },
  deleteButtonText: {
    color: "#b91c1c",
    fontWeight: "700",
  },
  threadCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    backgroundColor: "#fbfdff",
    gap: 2,
  },
  threadCardActive: {
    borderWidth: 1,
    borderColor: "#93c5fd",
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    backgroundColor: "#eff6ff",
    gap: 2,
  },
  threadRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  chatHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 6,
  },
  backLink: {
    color: "#1d4ed8",
    fontWeight: "700",
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
  tabLabelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  badge: {
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: "#dc2626",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 5,
  },
  badgeText: {
    color: "white",
    fontSize: 11,
    fontWeight: "700",
  },
  success: {
    color: "#0b7a2f",
  },
  error: {
    color: "#a11",
  },
});
