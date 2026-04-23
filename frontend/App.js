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
  loadStoredAuth,
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

const palette = {
  bg: "#f4f7fb",
  card: "#ffffff",
  border: "#d9e2ef",
  text: "#142033",
  subtext: "#617086",
  primary: "#4f46e5",
  primarySoft: "#ecebff",
  success: "#0f766e",
  successSoft: "#ccfbf1",
  warning: "#b45309",
  warningSoft: "#fef3c7",
  danger: "#b91c1c",
  dangerSoft: "#fee2e2",
  dark: "#1e293b",
};

function getListingMode(item) {
  if (item.listing_type === "buy") return "selling";
  if (item.iso_text?.toLowerCase().startsWith("iso:")) return "in_search_of";
  return "swapping";
}

function getApprovalTone(status) {
  if (status === "approved") {
    return { bg: "#dcfce7", color: "#166534", label: "Approved" };
  }
  if (status === "pending") {
    return { bg: "#fef3c7", color: "#92400e", label: "Pending" };
  }
  if (status === "rejected") {
    return { bg: "#fee2e2", color: "#991b1b", label: "Rejected" };
  }
  return { bg: "#e2e8f0", color: "#334155", label: status || "Unknown" };
}

function stars(value) {
  const rounded = Math.round(Number(value) || 0);
  return "★".repeat(rounded) + "☆".repeat(5 - rounded);
}

function formatRating(item) {
  const count = Number(item.rating_count || 0);
  const avg = Number(item.average_rating || 0);
  if (!count) return "No ratings yet";
  return `${stars(avg)} ${avg.toFixed(1)} (${count})`;
}

function AuthGate() {
  const dispatch = useDispatch();
  const auth = useSelector(selectAuth);

  const onLogin = () => dispatch(loginUser());
  const onRegister = () => dispatch(registerUser());

  return (
    <ScrollView contentContainerStyle={styles.authScroll}>
      <View style={styles.authHero}>
        <Text style={styles.authEyebrow}>BOARD GAME BUY • SELL • SWAP</Text>
        <Text style={styles.authHeading}>BoredGames Marketplace</Text>
        <Text style={styles.authSubheading}>
          Discover campus-friendly trades, sell games you are done with, and connect with other players.
        </Text>
      </View>

      <View style={styles.authCard}>
        <Text style={styles.sectionTitle}>Get started</Text>
        <TextInput
          style={styles.input}
          placeholder="Email"
          autoCapitalize="none"
          value={auth.form.email}
          onChangeText={(value) => dispatch(setCredentialsForm({ field: "email", value }))}
        />
        <TextInput
          style={styles.input}
          placeholder="Username"
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
            <Text style={styles.primaryButtonText}>
              {auth.status === "loading" ? "Logging in..." : "Login"}
            </Text>
          </Pressable>
        </View>

        {auth.registerSuccess ? <Text style={styles.success}>Account created. Now log in.</Text> : null}
        {auth.registerError ? <Text style={styles.error}>{auth.registerError}</Text> : null}
        {auth.error ? <Text style={styles.error}>{auth.error}</Text> : null}
      </View>
    </ScrollView>
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
    if (!auth.token) return undefined;
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

  const ownerName = (ownerId) => {
    const user = listings.usersById[ownerId];
    if (!user) return `User #${ownerId}`;
    return user.profile_display_name || user.username || user.email || `User #${ownerId}`;
  };

  const listingOwnerName = (listing) => listing?.owner_display_name || ownerName(listing?.owner);

  const listingTitleById = (listingId) => {
    if (!listingId) return "General chat";
    const listing = listings.items.find((item) => Number(item.id) === Number(listingId));
    return listing?.title || `Listing #${listingId}`;
  };

  const messageThreads = useMemo(() => {
    if (!auth.userId) return [];
    const threadMap = new Map();

    messages.items.forEach((message) => {
      const otherUserId =
        Number(message.sender) === Number(auth.userId) ? message.recipient : message.sender;
      if (Number(otherUserId) === Number(auth.userId)) return;

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
    if (!selectedThread || !auth.userId) return [];
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

      const mode = getListingMode(item);
      const matchesFilter = feedFilter === "all" || feedFilter === mode;
      return matchesText && matchesFilter;
    });
  }, [listings.items, searchText, feedFilter]);

  const feedStats = useMemo(() => {
    return {
      total: listings.items.length,
      selling: listings.items.filter((item) => getListingMode(item) === "selling").length,
      swapping: listings.items.filter((item) => getListingMode(item) === "swapping").length,
      iso: listings.items.filter((item) => getListingMode(item) === "in_search_of").length,
    };
  }, [listings.items]);

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
      Alert.alert("Listing posted", "Your listing was submitted successfully.");
      setActiveTab("listings");
      dispatch(fetchListings());
      dispatch(fetchMyListings());
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

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <View style={styles.topBarTextWrap}>
          <Text style={styles.brand}>BoredGames Marketplace</Text>
          <Text style={styles.topMeta}>
            Signed in as {auth.profileName || ownerName(auth.userId)}
          </Text>
        </View>
        <View style={styles.topBadge}>
          <Text style={styles.topBadgeText}>{messages.unreadCount || 0} new</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {activeTab === "listings" ? (
          <>
            <View style={styles.heroCard}>
              <Text style={styles.heroEyebrow}>Campus board game exchange</Text>
              <Text style={styles.heroTitle}>Buy, sell, swap, and message collectors in one place.</Text>
              <Text style={styles.heroText}>
                Browse approved listings, see reputation at a glance, and connect with owners instantly.
              </Text>

              <View style={styles.statsRow}>
                <View style={styles.statPill}>
                  <Text style={styles.statNumber}>{feedStats.total}</Text>
                  <Text style={styles.statLabel}>Listings</Text>
                </View>
                <View style={styles.statPill}>
                  <Text style={styles.statNumber}>{feedStats.selling}</Text>
                  <Text style={styles.statLabel}>Selling</Text>
                </View>
                <View style={styles.statPill}>
                  <Text style={styles.statNumber}>{feedStats.swapping}</Text>
                  <Text style={styles.statLabel}>Swaps</Text>
                </View>
                <View style={styles.statPill}>
                  <Text style={styles.statNumber}>{feedStats.iso}</Text>
                  <Text style={styles.statLabel}>ISO</Text>
                </View>
              </View>
            </View>

            <View style={styles.searchBar}>
              <TextInput
                style={styles.searchInput}
                placeholder="Search listings, game names, ISO notes..."
                value={searchText}
                onChangeText={setSearchText}
              />
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Marketplace Feed</Text>

              <View style={styles.rowWrap}>
                {["all", "selling", "swapping", "in_search_of"].map((filter) => (
                  <Pressable
                    key={filter}
                    style={feedFilter === filter ? styles.filterChipActive : styles.filterChip}
                    onPress={() => setFeedFilter(filter)}
                  >
                    <Text style={feedFilter === filter ? styles.filterChipTextActive : styles.filterChipText}>
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
                  renderItem={({ item }) => {
                    const approval = getApprovalTone(item.approval_status);
                    return (
                      <Pressable
                        style={styles.listingCard}
                        onPress={() => {
                          if (Number(item.owner) === Number(auth.userId)) {
                            Alert.alert("Your listing", "This is your own listing, so messaging is disabled.");
                            setSelectedListingId(item.id);
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
                        ) : (
                          <View style={styles.imagePlaceholder}>
                            <Text style={styles.imagePlaceholderText}>No image</Text>
                          </View>
                        )}

                        <View style={styles.listingHeaderRow}>
                          <View style={styles.listingHeaderText}>
                            <Text style={styles.listTitle}>{item.title}</Text>
                            <Text style={styles.subtleText}>Owner: {listingOwnerName(item)}</Text>
                          </View>
                          <View style={styles.rightPills}>
                            <View style={styles.typePill}>
                              <Text style={styles.typePillText}>
                                {listingTypeLabels[item.listing_type] || item.listing_type}
                              </Text>
                            </View>
                            {item.approval_status ? (
                              <View style={[styles.approvalPill, { backgroundColor: approval.bg }]}>
                                <Text style={[styles.approvalPillText, { color: approval.color }]}>
                                  {approval.label}
                                </Text>
                              </View>
                            ) : null}
                          </View>
                        </View>

                        <Text style={styles.listingBodyText}>
                          {item.description || "No description provided."}
                        </Text>

                        <View style={styles.metaRow}>
                          {item.price !== null ? <Text style={styles.price}>${item.price}</Text> : null}
                          <Text style={styles.ratingText}>{formatRating(item)}</Text>
                        </View>

                        {item.iso_text ? <Text style={styles.isoText}>{item.iso_text}</Text> : null}

                        {item.tags?.length ? (
                          <View style={styles.tagsRow}>
                            {item.tags.map((tag) => (
                              <View key={`${item.id}-${tag}`} style={styles.tagChip}>
                                <Text style={styles.tagChipText}>{tag}</Text>
                              </View>
                            ))}
                          </View>
                        ) : null}
                      </Pressable>
                    );
                  }}
                />
              )}
            </View>

            {selectedListing ? (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Listing Details</Text>
                <Text style={styles.detailTitle}>{selectedListing.title}</Text>
                <Text style={styles.subtleText}>Posted by {listingOwnerName(selectedListing)}</Text>
                <Text style={styles.ratingDetail}>{formatRating(selectedListing)}</Text>
                <Text style={styles.listingBodyText}>
                  {selectedListing.description || "No description provided."}
                </Text>

                {selectedListing.price !== null ? (
                  <Text style={styles.price}>${selectedListing.price}</Text>
                ) : null}

                {selectedListing.iso_text ? (
                  <Text style={styles.isoText}>{selectedListing.iso_text}</Text>
                ) : null}

                {selectedListing.tags?.length ? (
                  <View style={styles.tagsRow}>
                    {selectedListing.tags.map((tag) => (
                      <View key={`detail-${selectedListing.id}-${tag}`} style={styles.tagChip}>
                        <Text style={styles.tagChipText}>{tag}</Text>
                      </View>
                    ))}
                  </View>
                ) : null}

                <Text style={styles.sectionSubTitle}>Message Listing Owner</Text>
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
            <Text style={styles.sectionTitle}>Messages</Text>

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
                        <Text style={styles.badgeText}>
                          {item.unreadCount > 99 ? "99+" : item.unreadCount}
                        </Text>
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
                      Number(item.sender) === Number(auth.userId)
                        ? styles.messageBubbleMine
                        : styles.messageBubbleTheirs
                    }
                  >
                    <Text style={styles.messageText}>{item.content}</Text>
                  </View>
                )}
              />
            ) : null}

            {selectedThread || selectedListing ? (
              <View style={styles.messageComposeCard}>
                <Text style={styles.sectionSubTitle}>
                  Message{" "}
                  {selectedRecipientName ||
                    (selectedThread ? ownerName(selectedThread.otherUserId) : listingOwnerName(selectedListing))}
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

            {messages.listStatus === "loading" ? <ActivityIndicator /> : null}
            {messages.listError ? <Text style={styles.error}>{messages.listError}</Text> : null}
          </View>
        ) : null}

        {activeTab === "profile" ? (
          <>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Profile</Text>
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

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>My Listings</Text>
              {listings.myStatus === "loading" ? (
                <ActivityIndicator />
              ) : (
                <FlatList
                  data={listings.myItems}
                  scrollEnabled={false}
                  keyExtractor={(item) => `my-${item.id}`}
                  ListEmptyComponent={<Text style={styles.subtleText}>You have no listings yet.</Text>}
                  renderItem={({ item }) => {
                    const approval = getApprovalTone(item.approval_status);
                    return (
                      <View style={styles.myListingCard}>
                        <View style={styles.listingHeaderRow}>
                          <Text style={styles.listTitle}>{item.title}</Text>
                          {item.approval_status ? (
                            <View style={[styles.approvalPill, { backgroundColor: approval.bg }]}>
                              <Text style={[styles.approvalPillText, { color: approval.color }]}>
                                {approval.label}
                              </Text>
                            </View>
                          ) : null}
                        </View>

                        <Text style={styles.subtleText}>
                          {item.listing_type === "buy" ? "Selling" : "Swap/ISO"}
                          {item.price !== null ? ` • $${item.price}` : ""}
                        </Text>
                        <Text style={styles.subtleText}>{formatRating(item)}</Text>
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
                    );
                  }}
                />
              )}
              {listings.myError ? <Text style={styles.error}>{listings.myError}</Text> : null}
              {listings.deleteError ? <Text style={styles.error}>{listings.deleteError}</Text> : null}
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Add Listing</Text>
              <View style={styles.rowWrap}>
                {["selling", "swapping", "in_search_of"].map((mode) => (
                  <Pressable
                    key={mode}
                    style={listings.draft.mode === mode ? styles.filterChipActive : styles.filterChip}
                    onPress={() => dispatch(setDraftField({ field: "mode", value: mode }))}
                  >
                    <Text style={listings.draft.mode === mode ? styles.filterChipTextActive : styles.filterChipText}>
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
                  placeholder={
                    listings.draft.mode === "in_search_of"
                      ? "What are you looking for?"
                      : "What are you offering/wanting?"
                  }
                  value={listings.draft.iso_text}
                  onChangeText={(value) => dispatch(setDraftField({ field: "iso_text", value }))}
                />
              )}

              <TextInput
                style={styles.input}
                placeholder="Tags (comma-separated)"
                value={listings.draft.tags}
                onChangeText={(value) => dispatch(setDraftField({ field: "tags", value }))}
              />

              {listings.draft.image ? (
                <Image source={{ uri: listings.draft.image.uri }} style={styles.previewImage} />
              ) : (
                <View style={styles.imagePlaceholderLarge}>
                  <Text style={styles.imagePlaceholderText}>No image selected</Text>
                </View>
              )}

              <Pressable style={styles.secondaryButton} onPress={pickListingImage}>
                <Text style={styles.secondaryButtonText}>Upload Listing Image</Text>
              </Pressable>
              <Pressable style={styles.primaryButton} onPress={submitListing}>
                <Text style={styles.primaryButtonText}>Post Listing</Text>
              </Pressable>

              {listings.createError ? <Text style={styles.error}>{listings.createError}</Text> : null}
            </View>
          </>
        ) : null}
      </ScrollView>

      <View style={styles.tabBar}>
        <Pressable
          style={activeTab === "listings" ? styles.tabActive : styles.tab}
          onPress={() => setActiveTab("listings")}
        >
          <Text style={activeTab === "listings" ? styles.tabTextActive : styles.tabText}>Marketplace</Text>
        </Pressable>

        <Pressable
          style={activeTab === "messages" ? styles.tabActive : styles.tab}
          onPress={() => setActiveTab("messages")}
        >
          <View style={styles.tabLabelRow}>
            <Text style={activeTab === "messages" ? styles.tabTextActive : styles.tabText}>Messages</Text>
            {messages.unreadCount > 0 ? (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{messages.unreadCount > 99 ? "99+" : messages.unreadCount}</Text>
              </View>
            ) : null}
          </View>
        </Pressable>

        <Pressable
          style={activeTab === "profile" ? styles.tabActive : styles.tab}
          onPress={() => setActiveTab("profile")}
        >
          <Text style={activeTab === "profile" ? styles.tabTextActive : styles.tabText}>Profile</Text>
        </Pressable>
      </View>
    </View>
  );
}

function RootApp() {
  const dispatch = useDispatch();
  const auth = useSelector(selectAuth);

  useEffect(() => {
    dispatch(loadStoredAuth());
  }, [dispatch]);

  if (!auth.authChecked) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator style={{ marginTop: 40 }} />
        <StatusBar style="dark" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {!auth.token ? <AuthGate /> : <MarketplaceApp />}
      <StatusBar style="dark" />
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
    backgroundColor: palette.bg,
  },
  authScroll: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 18,
    gap: 16,
  },
  authHero: {
    backgroundColor: "#1f2454",
    borderRadius: 24,
    padding: 22,
    shadowColor: "#0f172a",
    shadowOpacity: 0.12,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
    elevation: 5,
  },
  authEyebrow: {
    color: "#c7d2fe",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
    marginBottom: 8,
  },
  authHeading: {
    fontSize: 30,
    fontWeight: "800",
    color: "#ffffff",
    marginBottom: 8,
  },
  authSubheading: {
    color: "#dbe4ff",
    lineHeight: 21,
  },
  authCard: {
    backgroundColor: palette.card,
    borderRadius: 22,
    padding: 18,
    borderWidth: 1,
    borderColor: palette.border,
    gap: 10,
  },
  topBar: {
    backgroundColor: "#1f2454",
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  topBarTextWrap: {
    flex: 1,
    paddingRight: 10,
  },
  brand: {
    color: "white",
    fontSize: 22,
    fontWeight: "800",
  },
  topMeta: {
    color: "#c7d2fe",
    marginTop: 4,
  },
  topBadge: {
    backgroundColor: "#312e81",
    borderWidth: 1,
    borderColor: "#4f46e5",
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 999,
  },
  topBadgeText: {
    color: "#e0e7ff",
    fontWeight: "700",
    fontSize: 12,
  },
  scrollContent: {
    paddingHorizontal: 14,
    paddingVertical: 14,
    gap: 12,
  },
  heroCard: {
    backgroundColor: "#eef2ff",
    borderRadius: 24,
    padding: 18,
    borderWidth: 1,
    borderColor: "#c7d2fe",
    gap: 8,
  },
  heroEyebrow: {
    fontSize: 12,
    fontWeight: "800",
    color: "#4338ca",
    letterSpacing: 1,
  },
  heroTitle: {
    fontSize: 24,
    fontWeight: "800",
    color: "#1e1b4b",
    lineHeight: 30,
  },
  heroText: {
    color: "#475569",
    lineHeight: 20,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 6,
  },
  statPill: {
    backgroundColor: "#ffffff",
    borderRadius: 18,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: "#dbe4ff",
    minWidth: 78,
  },
  statNumber: {
    fontSize: 18,
    fontWeight: "800",
    color: "#1e1b4b",
  },
  statLabel: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 2,
  },
  searchBar: {
    backgroundColor: palette.card,
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: palette.border,
  },
  searchInput: {
    fontSize: 15,
    color: palette.text,
  },
  card: {
    backgroundColor: palette.card,
    borderRadius: 22,
    padding: 14,
    borderWidth: 1,
    borderColor: palette.border,
    gap: 10,
  },
  sectionTitle: {
    fontWeight: "800",
    fontSize: 18,
    color: palette.text,
  },
  sectionSubTitle: {
    fontWeight: "700",
    fontSize: 15,
    marginTop: 4,
    color: palette.text,
  },
  input: {
    borderWidth: 1,
    borderColor: "#cdd7e5",
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 11,
    backgroundColor: "#fff",
    color: palette.text,
  },
  multilineInput: {
    minHeight: 80,
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
    backgroundColor: palette.primary,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
    flex: 1,
  },
  secondaryButton: {
    backgroundColor: palette.primarySoft,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
    flex: 1,
  },
  disabledButton: {
    backgroundColor: "#a8b3c7",
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "white",
    fontWeight: "800",
  },
  secondaryButtonText: {
    color: palette.primary,
    fontWeight: "800",
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d3dce9",
    backgroundColor: "#f8fafc",
  },
  filterChipActive: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#a5b4fc",
    backgroundColor: "#eef2ff",
  },
  filterChipText: {
    color: "#334155",
    fontWeight: "600",
  },
  filterChipTextActive: {
    color: "#4338ca",
    fontWeight: "800",
  },
  listingCard: {
    borderWidth: 1,
    borderColor: "#dde5f1",
    borderRadius: 20,
    padding: 12,
    marginBottom: 10,
    gap: 8,
    backgroundColor: "#fcfdff",
  },
  listingImage: {
    width: "100%",
    height: 180,
    borderRadius: 16,
    backgroundColor: "#dbe6f7",
  },
  previewImage: {
    width: "100%",
    height: 200,
    borderRadius: 16,
    backgroundColor: "#dbe6f7",
  },
  imagePlaceholder: {
    width: "100%",
    height: 180,
    borderRadius: 16,
    backgroundColor: "#e9eef7",
    alignItems: "center",
    justifyContent: "center",
  },
  imagePlaceholderLarge: {
    width: "100%",
    height: 200,
    borderRadius: 16,
    backgroundColor: "#e9eef7",
    alignItems: "center",
    justifyContent: "center",
  },
  imagePlaceholderText: {
    color: "#64748b",
    fontWeight: "700",
  },
  listingHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 10,
  },
  listingHeaderText: {
    flex: 1,
    gap: 2,
  },
  rightPills: {
    alignItems: "flex-end",
    gap: 6,
  },
  typePill: {
    backgroundColor: "#ede9fe",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
  },
  typePillText: {
    fontSize: 12,
    color: "#5b21b6",
    fontWeight: "800",
  },
  approvalPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
  },
  approvalPillText: {
    fontSize: 12,
    fontWeight: "800",
  },
  listTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: palette.text,
  },
  listingBodyText: {
    color: "#334155",
    lineHeight: 20,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
    flexWrap: "wrap",
  },
  ratingText: {
    color: "#7c3aed",
    fontWeight: "700",
  },
  ratingDetail: {
    color: "#7c3aed",
    fontWeight: "700",
    marginBottom: 2,
  },
  isoText: {
    color: "#475569",
    fontStyle: "italic",
  },
  tagsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  tagChip: {
    backgroundColor: "#eff6ff",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  tagChipText: {
    color: "#1d4ed8",
    fontSize: 12,
    fontWeight: "700",
  },
  detailTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: palette.text,
  },
  price: {
    fontSize: 18,
    fontWeight: "800",
    color: "#166534",
  },
  subtleText: {
    color: palette.subtext,
  },
  threadCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 16,
    padding: 12,
    marginBottom: 8,
    backgroundColor: "#fbfdff",
    gap: 4,
  },
  threadCardActive: {
    borderWidth: 1,
    borderColor: "#a5b4fc",
    borderRadius: 16,
    padding: 12,
    marginBottom: 8,
    backgroundColor: "#eef2ff",
    gap: 4,
  },
  threadRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  messageBubbleMine: {
    alignSelf: "flex-end",
    backgroundColor: "#e0e7ff",
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 6,
    maxWidth: "84%",
  },
  messageBubbleTheirs: {
    alignSelf: "flex-start",
    backgroundColor: "#f1f5f9",
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 6,
    maxWidth: "84%",
  },
  messageText: {
    color: "#0f172a",
  },
  messageComposeCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 18,
    padding: 12,
    gap: 8,
    backgroundColor: "#fbfdff",
    marginBottom: 10,
  },
  myListingCard: {
    borderWidth: 1,
    borderColor: "#d8e2f0",
    borderRadius: 18,
    padding: 12,
    marginBottom: 8,
    gap: 6,
    backgroundColor: "#fbfdff",
  },
  deleteButton: {
    marginTop: 6,
    backgroundColor: palette.dangerSoft,
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: "center",
  },
  deleteButtonText: {
    color: palette.danger,
    fontWeight: "800",
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
    paddingVertical: 11,
    borderRadius: 14,
    backgroundColor: "#edf2f7",
  },
  tabActive: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 11,
    borderRadius: 14,
    backgroundColor: "#e0e7ff",
  },
  tabText: {
    color: "#475569",
    fontWeight: "700",
  },
  tabTextActive: {
    color: "#3730a3",
    fontWeight: "800",
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
    fontWeight: "800",
  },
  success: {
    color: palette.success,
    fontWeight: "600",
  },
  error: {
    color: palette.danger,
    fontWeight: "600",
  },
});