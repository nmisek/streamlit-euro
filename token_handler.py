import streamlit as st
import streamlit.components.v1 as components

def token_state_init():
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


def sendTokenRefreshMessageToParent():
    post_message_script = """
    <script>
        console.log("Sending token refresh message to parent 2")
        // Send a postMessage event with the message
        const message = {
            type: "NEXTMV_TOKEN_REFRESH",
        };
        window.parent.parent.parent.postMessage(message, '*');
        console.log("Message sent to parent 2")
    </script>
    """

    components.html(post_message_script)

# def sendTokenRefreshMessageToParent():
#     st.write("Sending token refresh message to parent")
#     components.html("<script>sendTokenRefreshMessageToParent()</script>", height=0)

