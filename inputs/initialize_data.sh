
export no_proxy=$no_proxy

data_path=./inputs/习近平：在全国科技大会、国家科学技术奖励大会、两院院士大会上的讲话

# make dir & upload files
echo "Creating data directory at $data_path"
mkdir -p $data_path/input

# initializing
echo "Initializing data directory"
python -m graphrag.index --init --root $data_path

echo "Please manually upload your data files to \`$data_path/input\`"
read -p "Press enter when finished"

# indexing
echo "Start indexing data"
python -m graphrag.index --root $data_path

# searching
echo "Start testing with global search"
python -m graphrag.query \
    --root $data_path \
    --method global \
    --community_level 2 \
    --response_type "Multiple Paragraphs" \
    "What are the top themes in this story?"

echo "Start testing with local search"
python -m graphrag.query \
    --root $data_path \
    --method local \
    --community_level 2 \
    --response_type "Multiple Paragraphs" \
    "What are the top themes in this story?"