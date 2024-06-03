import streamlit as st
import streamlit.components.v1 as components

def init_auth_state():
    if "NEXTMV_API_KEY" in st.secrets:
        api_key = st.secrets["NEXTMV_API_KEY"]
        st.session_state.api_key = st.secrets["NEXTMV_API_KEY"]
        st.session_state.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        st.session_state.token_init_complete = True
    if "token_init_complete" not in st.session_state or not st.session_state.token_init_complete:
            
        # Get the query parameters
        query_params = st.query_params
        # Get the value of the "token" parameter
        token = query_params.get("token", "")
        # Get the value of the "account" parameter
        account = query_params.get("account", "")
        if token == "" or account == "":
            st.error("Token and account missing in query params.")
        # Set the token and account in session state
        st.session_state.token = token
        st.session_state.account = account
        st.session_state.token_expired = False
        st.session_state.token_refresh_count = 0
        st.session_state.token_init_complete = True
        st.session_state.headers = {"Authorization": f"Bearer {token}", "nextmv-account": account, "Content-Type": "application/json"}


def sendTokenRefreshMessageToParent():
    post_message_script = """
    <script>
        // Send a postMessage event with the message
        const message = {
            type: "NEXTMV_TOKEN_REFRESH",
        };
        window.parent.parent.parent.postMessage(message, '*');
    </script>
    """

    components.html(post_message_script)

