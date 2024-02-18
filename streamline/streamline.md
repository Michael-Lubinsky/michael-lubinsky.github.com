
streamlit run myapp.py

https://medium.com/codefile/streamlit-navigating-multi-page-apps-with-v1-30-0-87146f997f51

```
import streamlit as st

st.header("Multipage navigation")

if st.button("Home page"):
    st.switch_page("multipage-nav1.py")
if st.button("Page 1"):
    st.switch_page("pages/page1.py")
if st.button("Page 2"):
    st.switch_page("pages/page2.py")
```
